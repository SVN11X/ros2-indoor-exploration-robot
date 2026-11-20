#!/usr/bin/env python3
"""
Analiza las cinco pruebas de giro de 360° ejecutadas en Gazebo.

Entradas esperadas, en la misma carpeta del script:
    prueba_giro_sim_1.log
    ...
    prueba_giro_sim_5.log

Salidas:
    tabla_odom_giro_sim.tex
    giro_error_barras_sim.png
    giro_error_barras_sim.pdf

El gráfico representa únicamente la simulación. Para cada prueba se utiliza
como giro de ejecución la referencia de Gazebo cuando el log la identifica
como independiente; de lo contrario se utiliza la odometría simulada.

Criterio para evitar gráficos vacíos:
1. Se grafica la desviación porcentual del giro ejecutado respecto de 360°.
2. Si todas las desviaciones son 0 %, se muestran los ángulos obtenidos y una
   línea de referencia en 360°.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
N_PRUEBAS = 5
GIRO_TEORICO = 360.0
CRITERIO_MAX_PCT = 5.0
TOL_CASI_CERO = 1e-6
TOL_IGUALES = 0.005


@dataclass(frozen=True)
class ResultadoGiroSim:
    prueba: int
    giro_teorico: float
    delta_odom: float
    delta_gt: float
    fuente_gt: str
    gt_independiente: bool
    giro_ejecucion: float
    error_odom_gt_pct: float
    desviacion_objetivo_deg: float
    desviacion_objetivo_pct: float


def leer_archivo_clave_valor(ruta: str) -> dict[str, str]:
    datos: dict[str, str] = {}
    with open(ruta, encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if "," not in linea:
                print(
                    f"AVISO: línea {numero_linea} ignorada en "
                    f"{os.path.basename(ruta)}: {linea!r}"
                )
                continue
            clave, valor = linea.split(",", 1)
            datos[clave.strip()] = valor.strip()
    return datos


def es_ground_truth_independiente(fuente: str, tiene_delta_real: bool) -> bool:
    if not tiene_delta_real:
        return False

    texto = fuente.strip().lower()
    indicadores_no_independientes = (
        "fallback",
        "odom",
        "odometr",
        "no disponible",
        "respaldo",
    )
    return not any(indicador in texto for indicador in indicadores_no_independientes)


def todos_casi_cero(valores: Iterable[float]) -> bool:
    arreglo = np.asarray(list(valores), dtype=float)
    return arreglo.size > 0 and bool(
        np.allclose(arreglo, 0.0, rtol=0.0, atol=TOL_CASI_CERO)
    )


def valores_iguales(valores: Iterable[float]) -> bool:
    arreglo = np.asarray(list(valores), dtype=float)
    return arreglo.size > 1 and bool(
        np.allclose(arreglo, arreglo[0], rtol=0.0, atol=TOL_IGUALES)
    )


def leer_logs_sim() -> list[ResultadoGiroSim]:
    resultados: list[ResultadoGiroSim] = []

    for numero in range(1, N_PRUEBAS + 1):
        ruta = os.path.join(SCRIPT_DIR, f"prueba_giro_sim_{numero}.log")
        if not os.path.exists(ruta):
            print(f"AVISO: no se encuentra {ruta}; se omite la prueba {numero}.")
            continue

        fila = leer_archivo_clave_valor(ruta)

        try:
            prueba = int(fila.get("prueba", numero))
            giro_teorico = float(fila.get("giro_teorico_deg", GIRO_TEORICO))
            delta_odom = float(fila["delta_odom_deg"])

            tiene_delta_real = "delta_real_deg" in fila
            delta_gt = float(fila.get("delta_real_deg", delta_odom))
            fuente_gt = fila.get("fuente_real", "no indicada")
            gt_independiente = es_ground_truth_independiente(
                fuente_gt,
                tiene_delta_real,
            )

            giro_ejecucion = delta_gt if gt_independiente else delta_odom
            error_odom_gt_pct = (
                abs(delta_odom - delta_gt) / abs(delta_gt) * 100.0
                if gt_independiente and abs(delta_gt) > TOL_CASI_CERO
                else 0.0
            )
            desviacion_objetivo_deg = abs(giro_ejecucion - giro_teorico)
            desviacion_objetivo_pct = (
                desviacion_objetivo_deg / abs(giro_teorico) * 100.0
                if abs(giro_teorico) > TOL_CASI_CERO
                else 0.0
            )

            resultados.append(
                ResultadoGiroSim(
                    prueba=prueba,
                    giro_teorico=giro_teorico,
                    delta_odom=delta_odom,
                    delta_gt=delta_gt,
                    fuente_gt=fuente_gt,
                    gt_independiente=gt_independiente,
                    giro_ejecucion=giro_ejecucion,
                    error_odom_gt_pct=error_odom_gt_pct,
                    desviacion_objetivo_deg=desviacion_objetivo_deg,
                    desviacion_objetivo_pct=desviacion_objetivo_pct,
                )
            )
        except (KeyError, ValueError) as error:
            print(f"ERROR leyendo {ruta}: {error}")

    return sorted(resultados, key=lambda resultado: resultado.prueba)


def generar_latex(datos: list[ResultadoGiroSim]) -> None:
    fin = r"\\"
    datos_por_prueba = {dato.prueba: dato for dato in datos}

    lineas = [
        "% Generado por analizar_prueba_giro_sim.py",
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Resultados del giro de 360\textdegree{} en simulaci\'on (Gazebo).}",
        r"\label{tab:odom_giro_sim}",
        r"\small",
        r"\begin{tabular}{cccccc}",
        r"\hline",
        r"\textbf{Prueba} & \textbf{Te\'orico (\textdegree{})} & "
        r"\textbf{Odom. (\textdegree{})} & \textbf{Ref. Gazebo (\textdegree{})} & "
        r"\textbf{Error odom.-ref. (\%)} & \textbf{Desv. 360\textdegree{} (\%)} \\",
        r"\hline",
    ]

    errores: list[float] = []
    desviaciones: list[float] = []

    for numero in range(1, N_PRUEBAS + 1):
        dato = datos_por_prueba.get(numero)
        if dato is None:
            lineas.append(
                f"{numero} & {GIRO_TEORICO:.1f} & N/D & N/D & N/D & N/D {fin}"
            )
            continue

        etiqueta_gt = f"{dato.delta_gt:.2f}" if dato.gt_independiente else "N/I"
        etiqueta_error = (
            f"{dato.error_odom_gt_pct:.2f}\\%"
            if dato.gt_independiente
            else "N/A"
        )

        lineas.append(
            f"{numero} & {dato.giro_teorico:.1f} & {dato.delta_odom:.2f} & "
            f"{etiqueta_gt} & {etiqueta_error} & "
            f"{dato.desviacion_objetivo_pct:.2f}\\% {fin}"
        )

        if dato.gt_independiente:
            errores.append(dato.error_odom_gt_pct)
        desviaciones.append(dato.desviacion_objetivo_pct)

    lineas.append(r"\hline")
    if errores:
        lineas.append(
            rf"\multicolumn{{4}}{{r}}{{\textbf{{Error odom.-ref. medio}}}} & "
            rf"\textbf{{{np.mean(errores):.2f}\%}} & {fin}"
        )
    else:
        lineas.append(
            rf"\multicolumn{{4}}{{r}}{{\textbf{{Error odom.-ref. medio}}}} & "
            rf"\textbf{{N/A}} & {fin}"
        )

    lineas.append(
        rf"\multicolumn{{5}}{{r}}{{\textbf{{Desviaci\'on media respecto a 360\textdegree{{}}}}}} & "
        rf"\textbf{{{np.mean(desviaciones):.2f}\%}} {fin}"
    )
    lineas.extend([r"\hline", r"\end{tabular}", r"\end{table}"])

    ruta_salida = os.path.join(SCRIPT_DIR, "tabla_odom_giro_sim.tex")
    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas))
    print(f"LaTeX guardado en: {ruta_salida}")


def generar_grafico(datos: list[ResultadoGiroSim]) -> None:
    if not datos:
        print("AVISO: no hay datos de simulación para graficar.")
        return

    pruebas = [dato.prueba for dato in datos]
    desviaciones = [dato.desviacion_objetivo_pct for dato in datos]
    angulos = [dato.giro_ejecucion for dato in datos]
    x = np.arange(len(pruebas))

    fig, ax = plt.subplots(figsize=(10, 6))

    if not todos_casi_cero(desviaciones):
        modo = "porcentaje"
        valores = desviaciones
        barras = ax.bar(
            x,
            valores,
            width=0.58,
            color="steelblue",
            edgecolor="black",
            linewidth=0.7,
            label="Gazebo: giro simulado respecto a 360°",
            zorder=3,
        )
        ax.axhline(
            CRITERIO_MAX_PCT,
            color="red",
            linestyle="--",
            linewidth=1.3,
            alpha=0.75,
            label=f"Criterio máximo: {CRITERIO_MAX_PCT:.0f} %",
            zorder=2,
        )
        ax.set_ylabel("Desviación respecto al giro teórico de 360° (%)", fontsize=11)

        maximo_datos = max(valores, default=0.0)
        desplazamiento = max(maximo_datos * 0.025, 0.05)
        for barra, valor in zip(barras, valores):
            ax.text(
                barra.get_x() + barra.get_width() / 2,
                valor + desplazamiento,
                f"{valor:.2f} %",
                ha="center",
                va="bottom",
                fontsize=9,
            )
        maximo = max(maximo_datos, CRITERIO_MAX_PCT)
        ax.set_ylim(0, maximo * 1.28)
    else:
        modo = "angulo"
        valores = angulos
        ax.plot(
            x,
            valores,
            marker="o",
            linewidth=2,
            markersize=7,
            color="steelblue",
            label="Gazebo: giro obtenido",
            zorder=3,
        )
        ax.axhline(
            GIRO_TEORICO,
            color="red",
            linestyle="--",
            linewidth=1.3,
            alpha=0.75,
            label=f"Referencia teórica: {GIRO_TEORICO:.0f}°",
            zorder=2,
        )
        ax.set_ylabel("Giro obtenido en Gazebo (°)", fontsize=11)

        for posicion, valor in zip(x, valores):
            ax.annotate(
                f"{valor:.2f}°",
                (posicion, valor),
                xytext=(0, 9),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )
        minimo = min(valores + [GIRO_TEORICO])
        maximo = max(valores + [GIRO_TEORICO])
        margen = max((maximo - minimo) * 0.35, 2.0)
        ax.set_ylim(max(0.0, minimo - margen), maximo + margen)

    ax.set_xlabel("Repetición", fontsize=12)
    ax.set_title("Giro completo de 360°: simulación en Gazebo", fontsize=14, pad=16)
    ax.set_xticks(x)
    ax.set_xticklabels(pruebas)
    ax.grid(axis="y", alpha=0.25, zorder=0)


    ax.legend(
        title="Entorno de prueba",
        fontsize=9.5,
        title_fontsize=10,
        loc="upper right",
    )
    fig.tight_layout()

    for extension in ("png", "pdf"):
        ruta = os.path.join(SCRIPT_DIR, f"giro_error_barras_sim.{extension}")
        fig.savefig(ruta, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("Gráfico guardado: giro_error_barras_sim.png / .pdf")


def imprimir_resumen(datos: list[ResultadoGiroSim]) -> None:
    print(
        f"\n{'Prueba':>7} {'Odom (°)':>11} {'Ref. (°)':>11} "
        f"{'Fuente':>20} {'Error odom.-ref.':>18} {'Desv. 360°':>13}"
    )
    print("-" * 88)

    for dato in datos:
        fuente_corta = "Gazebo" if dato.gt_independiente else "Odom/fallback"
        error_ref = (
            f"{dato.error_odom_gt_pct:.2f} %"
            if dato.gt_independiente
            else "N/A"
        )
        print(
            f"{dato.prueba:>7} {dato.delta_odom:>11.2f} "
            f"{dato.delta_gt:>11.2f} {fuente_corta:>20} "
            f"{error_ref:>18} {dato.desviacion_objetivo_pct:>11.2f} %"
        )

    desviaciones = [dato.desviacion_objetivo_pct for dato in datos]
    print(
        f"\nDesviación media respecto a 360°: "
        f"{np.mean(desviaciones):.2f} %"
    )


def main() -> None:
    print("\n" + "=" * 78)
    print("ANÁLISIS: giro de 360° simulado en Gazebo")
    print("=" * 78)

    datos = leer_logs_sim()
    if not datos:
        print("Sin datos. Ejecuta run_prueba_giro_sim.sh primero.")
        return

    imprimir_resumen(datos)
    generar_latex(datos)
    generar_grafico(datos)

    print("\nArchivos generados:")
    print("  - tabla_odom_giro_sim.tex")
    print("  - giro_error_barras_sim.png / .pdf")


if __name__ == "__main__":
    main()