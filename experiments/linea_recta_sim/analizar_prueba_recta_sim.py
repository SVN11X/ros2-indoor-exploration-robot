#!/usr/bin/env python3
"""
Analiza las cinco pruebas de trayectoria rectilínea ejecutadas en Gazebo.

Entradas esperadas, en la misma carpeta del script:
    prueba_recta_sim_1.log
    ...
    prueba_recta_sim_5.log

Salidas:
    tabla_odom_recta_sim.tex
    odom_error_barras_sim.png
    odom_error_barras_sim.pdf

Criterio para evitar gráficos vacíos o engañosos:
1. Si existe un ground truth independiente de Gazebo y el error entre
   odometría y ground truth es apreciable, se grafica ese error.
2. Si el ground truth no es independiente, o si odometría y ground truth
   coinciden en todas las pruebas, se grafica la desviación del recorrido
   simulado respecto de los 2 m teóricos.
3. Si ambas métricas son exactamente cero, se muestran las distancias
   obtenidas y una línea de referencia en 2 m.

Este archivo representa únicamente simulaciones en Gazebo. No mezcla datos
obtenidos con el robot físico.
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
DIST_TEORICA = 2.00
CRITERIO_MAX_PCT = 5.0
TOL_CASI_CERO = 1e-6
TOL_IGUALES = 0.005


@dataclass(frozen=True)
class ResultadoRectaSim:
    prueba: int
    dist_teorica: float
    dist_odom: float
    dist_gt: float
    fuente_gt: str
    gt_independiente: bool
    error_odom_gt_pct: float
    desviacion_objetivo_pct: float
    distancia_ejecucion: float


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


def es_ground_truth_independiente(fuente: str, tiene_dist_real: bool) -> bool:
    if not tiene_dist_real:
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


def leer_logs_sim() -> list[ResultadoRectaSim]:
    resultados: list[ResultadoRectaSim] = []

    for numero in range(1, N_PRUEBAS + 1):
        ruta = os.path.join(SCRIPT_DIR, f"prueba_recta_sim_{numero}.log")
        if not os.path.exists(ruta):
            print(f"AVISO: no se encuentra {ruta}; se omite la prueba {numero}.")
            continue

        fila = leer_archivo_clave_valor(ruta)

        try:
            prueba = int(fila.get("prueba", numero))
            dist_teorica = float(fila.get("dist_teorica", DIST_TEORICA))
            dist_odom = float(fila["dist_odom"])

            tiene_dist_real = "dist_real" in fila
            dist_gt = float(fila.get("dist_real", dist_odom))
            fuente_gt = fila.get("fuente_real", "no indicada")
            gt_independiente = es_ground_truth_independiente(
                fuente_gt,
                tiene_dist_real,
            )

            distancia_ejecucion = dist_gt if gt_independiente else dist_odom

            error_odom_gt_pct = (
                abs(dist_odom - dist_gt) / abs(dist_gt) * 100.0
                if abs(dist_gt) > TOL_CASI_CERO
                else 0.0
            )
            desviacion_objetivo_pct = (
                abs(distancia_ejecucion - dist_teorica)
                / abs(dist_teorica)
                * 100.0
                if abs(dist_teorica) > TOL_CASI_CERO
                else 0.0
            )

            resultados.append(
                ResultadoRectaSim(
                    prueba=prueba,
                    dist_teorica=dist_teorica,
                    dist_odom=dist_odom,
                    dist_gt=dist_gt,
                    fuente_gt=fuente_gt,
                    gt_independiente=gt_independiente,
                    error_odom_gt_pct=error_odom_gt_pct,
                    desviacion_objetivo_pct=desviacion_objetivo_pct,
                    distancia_ejecucion=distancia_ejecucion,
                )
            )
        except (KeyError, ValueError) as error:
            print(f"ERROR leyendo {ruta}: {error}")

    return sorted(resultados, key=lambda resultado: resultado.prueba)


def seleccionar_metrica(
    datos: list[ResultadoRectaSim],
) -> dict[str, object]:
    errores_odom_gt = [dato.error_odom_gt_pct for dato in datos]
    desviaciones = [dato.desviacion_objetivo_pct for dato in datos]
    distancias = [dato.distancia_ejecucion for dato in datos]

    todos_gt_independientes = all(dato.gt_independiente for dato in datos)

    if todos_gt_independientes and not todos_casi_cero(errores_odom_gt):
        return {
            "modo": "porcentaje",
            "valores": errores_odom_gt,
            "ylabel": "Error de odometría respecto al ground truth de Gazebo (%)",
            "leyenda": "Gazebo: odometría simulada vs. ground truth",
        }

    if not todos_casi_cero(desviaciones):
        return {
            "modo": "porcentaje",
            "valores": desviaciones,
            "ylabel": "Desviación respecto a la trayectoria teórica de 2 m (%)",
            "leyenda": "Gazebo: recorrido simulado vs. 2 m teóricos",
        }

    return {
        "modo": "distancia",
        "valores": distancias,
        "ylabel": "Distancia recorrida en Gazebo (m)",
        "leyenda": "Gazebo: distancia obtenida",
    }


def generar_latex(datos: list[ResultadoRectaSim]) -> None:
    fin = r"\\"
    datos_por_prueba = {dato.prueba: dato for dato in datos}

    lineas = [
        "% Generado por analizar_prueba_recta_sim.py",
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Resultados de la trayectoria rectil\'inea de 2 m en simulaci\'on (Gazebo).}",
        r"\label{tab:odom_recta_sim}",
        r"\small",
        r"\begin{tabular}{cccccc}",
        r"\hline",
        r"\textbf{Prueba} & \textbf{Te\'orica (m)} & \textbf{Odom. (m)} & "
        r"\textbf{GT Gazebo (m)} & \textbf{Error odom.-GT (\%)} & "
        r"\textbf{Desv. 2 m (\%)} \\",
        r"\hline",
    ]

    errores: list[float] = []
    desviaciones: list[float] = []

    for numero in range(1, N_PRUEBAS + 1):
        dato = datos_por_prueba.get(numero)
        if dato is None:
            lineas.append(
                f"{numero} & {DIST_TEORICA:.2f} & N/D & N/D & N/D & N/D {fin}"
            )
            continue

        etiqueta_gt = f"{dato.dist_gt:.3f}" if dato.gt_independiente else "N/I"
        etiqueta_error_gt = (
            f"{dato.error_odom_gt_pct:.2f}\\%"
            if dato.gt_independiente
            else "N/A"
        )

        lineas.append(
            f"{numero} & {dato.dist_teorica:.2f} & {dato.dist_odom:.3f} & "
            f"{etiqueta_gt} & {etiqueta_error_gt} & "
            f"{dato.desviacion_objetivo_pct:.2f}\\% {fin}"
        )

        if dato.gt_independiente:
            errores.append(dato.error_odom_gt_pct)
        desviaciones.append(dato.desviacion_objetivo_pct)

    lineas.append(r"\hline")
    if errores:
        lineas.append(
            rf"\multicolumn{{4}}{{r}}{{\textbf{{Error odom.-GT medio}}}} & "
            rf"\textbf{{{np.mean(errores):.2f}\%}} & {fin}"
        )
    else:
        lineas.append(
            rf"\multicolumn{{4}}{{r}}{{\textbf{{Error odom.-GT medio}}}} & "
            rf"\textbf{{N/A}} & {fin}"
        )

    lineas.append(
        rf"\multicolumn{{5}}{{r}}{{\textbf{{Desviaci\'on media respecto a 2 m}}}} & "
        rf"\textbf{{{np.mean(desviaciones):.2f}\%}} {fin}"
    )
    lineas.extend([r"\hline", r"\end{tabular}", r"\end{table}"])

    ruta_salida = os.path.join(SCRIPT_DIR, "tabla_odom_recta_sim.tex")
    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas))
    print(f"LaTeX guardado en: {ruta_salida}")


def generar_grafico(datos: list[ResultadoRectaSim]) -> None:
    if not datos:
        print("AVISO: no hay datos de simulación para graficar.")
        return

    configuracion = seleccionar_metrica(datos)
    modo = str(configuracion["modo"])
    valores = [float(valor) for valor in configuracion["valores"]]
    pruebas = [dato.prueba for dato in datos]
    x = np.arange(len(pruebas))

    fig, ax = plt.subplots(figsize=(10, 6))

    if modo == "porcentaje":
        barras = ax.bar(
            x,
            valores,
            width=0.58,
            color="steelblue",
            edgecolor="black",
            linewidth=0.7,
            label=str(configuracion["leyenda"]),
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
        ax.plot(
            x,
            valores,
            marker="o",
            linewidth=2,
            markersize=7,
            color="steelblue",
            label=str(configuracion["leyenda"]),
            zorder=3,
        )
        ax.axhline(
            DIST_TEORICA,
            color="red",
            linestyle="--",
            linewidth=1.3,
            alpha=0.75,
            label=f"Referencia teórica: {DIST_TEORICA:.2f} m",
            zorder=2,
        )
        for posicion, valor in zip(x, valores):
            ax.annotate(
                f"{valor:.3f} m",
                (posicion, valor),
                xytext=(0, 9),
                textcoords="offset points",
                ha="center",
                fontsize=9,
            )
        minimo = min(valores + [DIST_TEORICA])
        maximo = max(valores + [DIST_TEORICA])
        margen = max((maximo - minimo) * 0.35, 0.05)
        ax.set_ylim(max(0.0, minimo - margen), maximo + margen)

    ax.set_xlabel("Repetición", fontsize=12)
    ax.set_ylabel(str(configuracion["ylabel"]), fontsize=11)
    ax.set_title("Trayectoria rectilínea de 2 m: simulación en Gazebo", fontsize=14, pad=16)
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
        ruta = os.path.join(SCRIPT_DIR, f"odom_error_barras_sim.{extension}")
        fig.savefig(ruta, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("Gráfico guardado: odom_error_barras_sim.png / .pdf")


def imprimir_resumen(datos: list[ResultadoRectaSim]) -> None:
    print(
        f"\n{'Prueba':>7} {'Odom (m)':>11} {'GT (m)':>11} "
        f"{'Fuente':>20} {'Error odom.-GT':>17} {'Desv. 2 m':>12}"
    )
    print("-" * 88)

    for dato in datos:
        fuente_corta = (
            "Gazebo"
            if dato.gt_independiente
            else "Odom/fallback"
        )
        error_gt = (
            f"{dato.error_odom_gt_pct:.2f} %"
            if dato.gt_independiente
            else "N/A"
        )
        print(
            f"{dato.prueba:>7} {dato.dist_odom:>11.3f} "
            f"{dato.dist_gt:>11.3f} {fuente_corta:>20} "
            f"{error_gt:>17} {dato.desviacion_objetivo_pct:>10.2f} %"
        )

    errores_validos = [
        dato.error_odom_gt_pct for dato in datos if dato.gt_independiente
    ]
    desviaciones = [dato.desviacion_objetivo_pct for dato in datos]

    if errores_validos:
        print(
            f"\nError odom.-GT medio en Gazebo: "
            f"{np.mean(errores_validos):.2f} %"
        )
    else:
        print("\nError odom.-GT medio en Gazebo: N/A (GT no independiente).")

    print(
        f"Desviación media respecto a 2 m: "
        f"{np.mean(desviaciones):.2f} %"
    )

    seleccion = seleccionar_metrica(datos)
    print(f"Métrica utilizada en el gráfico: {seleccion['ylabel']}")


def main() -> None:
    print("\n" + "=" * 78)
    print("ANÁLISIS: trayectoria rectilínea simulada en Gazebo")
    print("=" * 78)

    datos = leer_logs_sim()
    if not datos:
        print("Sin datos. Ejecuta run_prueba_recta_sim.sh primero.")
        return

    imprimir_resumen(datos)
    generar_latex(datos)
    generar_grafico(datos)

    print("\nArchivos generados:")
    print("  - tabla_odom_recta_sim.tex")
    print("  - odom_error_barras_sim.png / .pdf")


if __name__ == "__main__":
    main()