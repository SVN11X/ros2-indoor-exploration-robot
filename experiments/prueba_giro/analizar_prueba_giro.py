#!/usr/bin/env python3
"""
Analiza las cinco pruebas de giro de 360° ejecutadas con el robot físico.

Entradas esperadas, en la misma carpeta del script:
    prueba_giro_1.log
    ...
    prueba_giro_5.log
    angulos_reales.txt

Salidas:
    tabla_odom_giro_real.tex
    giro_deriva_barras.png
    giro_deriva_barras.pdf

Criterio para evitar gráficos vacíos:
1. Se grafica la desviación física absoluta respecto de 360°.
2. Si esa desviación es 0° en todas las pruebas, se grafica la diferencia
   entre odometría y medición física.
3. Si ambas métricas son 0°, se muestran los ángulos físicos obtenidos y una
   línea de referencia en 360°.

Este archivo representa únicamente ensayos del robot físico. No mezcla datos
de Gazebo.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ANGULO_FILE = os.path.join(SCRIPT_DIR, "angulos_reales.txt")
N_PRUEBAS = 5
GIRO_TEORICO = 360.0
CRITERIO_MAX_DEG = 10.0
TOL_CASI_CERO = 1e-6
TOL_IGUALES = 0.005


@dataclass(frozen=True)
class ResultadoGiroReal:
    prueba: int
    giro_teorico: float
    delta_odom: float
    angulo_fisico: float
    desviacion_fisica_deg: float
    desviacion_fisica_pct: float
    diferencia_odom_fisica_deg: float
    diferencia_odom_fisica_pct: float


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


def leer_angulos_reales() -> list[float]:
    if not os.path.exists(ANGULO_FILE):
        print(f"ERROR: no se encuentra '{ANGULO_FILE}'.")
        print("Crea el archivo con un ángulo físico por línea, en grados.")
        print("Ejemplo:")
        print("  366.2")
        print("  364.8")
        sys.exit(1)

    valores: list[float] = []
    with open(ANGULO_FILE, encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            try:
                valores.append(float(linea))
            except ValueError:
                print(
                    f"AVISO: línea {numero_linea} no numérica omitida en "
                    f"{os.path.basename(ANGULO_FILE)}: {linea!r}"
                )

    if len(valores) < N_PRUEBAS:
        print(
            f"ERROR: '{ANGULO_FILE}' contiene {len(valores)} mediciones; "
            f"se necesitan {N_PRUEBAS}."
        )
        sys.exit(1)

    return valores[:N_PRUEBAS]


def leer_log_numerico(ruta: str) -> dict[str, float]:
    datos: dict[str, float] = {}
    with open(ruta, encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            if "," not in linea:
                continue
            clave, valor = linea.split(",", 1)
            try:
                datos[clave.strip()] = float(valor.strip())
            except ValueError:
                print(
                    f"AVISO: valor no numérico omitido en "
                    f"{os.path.basename(ruta)}, línea {numero_linea}: {linea!r}"
                )
    return datos


def leer_resultados(angulos_fisicos: list[float]) -> list[ResultadoGiroReal]:
    resultados: list[ResultadoGiroReal] = []

    for numero, angulo_fisico in enumerate(angulos_fisicos, start=1):
        ruta = os.path.join(SCRIPT_DIR, f"prueba_giro_{numero}.log")
        if not os.path.exists(ruta):
            print(f"AVISO: no se encuentra {ruta}; se omite la prueba {numero}.")
            continue

        fila = leer_log_numerico(ruta)
        if "delta_odom_deg" not in fila:
            print(
                f"ERROR: falta 'delta_odom_deg' en {ruta}; "
                f"se omite la prueba {numero}."
            )
            continue

        giro_teorico = fila.get("giro_teorico_deg", GIRO_TEORICO)
        delta_odom = fila["delta_odom_deg"]
        desviacion_fisica_deg = abs(angulo_fisico - giro_teorico)
        desviacion_fisica_pct = (
            desviacion_fisica_deg / abs(giro_teorico) * 100.0
            if abs(giro_teorico) > TOL_CASI_CERO
            else 0.0
        )
        diferencia_odom_fisica_deg = abs(delta_odom - angulo_fisico)
        diferencia_odom_fisica_pct = (
            diferencia_odom_fisica_deg / abs(angulo_fisico) * 100.0
            if abs(angulo_fisico) > TOL_CASI_CERO
            else 0.0
        )

        resultados.append(
            ResultadoGiroReal(
                prueba=numero,
                giro_teorico=giro_teorico,
                delta_odom=delta_odom,
                angulo_fisico=angulo_fisico,
                desviacion_fisica_deg=desviacion_fisica_deg,
                desviacion_fisica_pct=desviacion_fisica_pct,
                diferencia_odom_fisica_deg=diferencia_odom_fisica_deg,
                diferencia_odom_fisica_pct=diferencia_odom_fisica_pct,
            )
        )

    return resultados


def seleccionar_metrica(
    datos: list[ResultadoGiroReal],
) -> dict[str, object]:
    desviaciones = [dato.desviacion_fisica_deg for dato in datos]
    diferencias = [dato.diferencia_odom_fisica_deg for dato in datos]
    angulos = [dato.angulo_fisico for dato in datos]

    if not todos_casi_cero(desviaciones):
        return {
            "modo": "grados_error",
            "valores": desviaciones,
            "ylabel": "Desviación física absoluta respecto a 360° (°)",
            "leyenda": "Robot físico: desviación medida respecto a 360°",
        }

    if not todos_casi_cero(diferencias):
        return {
            "modo": "grados_error",
            "valores": diferencias,
            "ylabel": "Diferencia entre odometría y medición física (°)",
            "leyenda": "Robot físico: odometría vs. medición física",
        }

    return {
        "modo": "angulo",
        "valores": angulos,
        "ylabel": "Ángulo físico obtenido (°)",
        "leyenda": "Robot físico: ángulo medido",
    }


def generar_latex(datos: list[ResultadoGiroReal]) -> None:
    desviaciones = [dato.desviacion_fisica_deg for dato in datos]
    media = f"{np.mean(desviaciones):.1f}" if desviaciones else "N/D"

    lineas = [
        "% Resultados de la prueba de giro con el robot físico.",
        "% Filas listas para incorporar en la tabla del capítulo de resultados.",
    ]

    datos_por_prueba = {dato.prueba: dato for dato in datos}
    for numero in range(1, N_PRUEBAS + 1):
        dato = datos_por_prueba.get(numero)
        if dato is None:
            lineas.append(
                f"        {numero} & {GIRO_TEORICO:.1f} & N/D & N/D \\\\"
            )
            continue

        signo = "+" if dato.angulo_fisico - dato.giro_teorico >= 0 else "-"
        lineas.append(
            f"        {numero} & {dato.giro_teorico:.1f} & "
            f"{dato.angulo_fisico:.1f} & "
            f"{signo}{dato.desviacion_fisica_deg:.1f} \\\\"
        )

    lineas.append(
        f"        \\multicolumn{{3}}{{r}}{{\\textbf{{Desviación media}}}} & "
        f"\\textbf{{{media}°}} \\\\"
    )

    ruta_salida = os.path.join(SCRIPT_DIR, "tabla_odom_giro_real.tex")
    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas))
    print(f"LaTeX guardado en: {ruta_salida}")


def generar_grafico(datos: list[ResultadoGiroReal]) -> None:
    if not datos:
        print("AVISO: no hay datos físicos para graficar.")
        return

    configuracion = seleccionar_metrica(datos)
    modo = str(configuracion["modo"])
    valores = [float(valor) for valor in configuracion["valores"]]
    pruebas = [dato.prueba for dato in datos]
    x = np.arange(len(pruebas))

    fig, ax = plt.subplots(figsize=(10, 6))

    if modo == "grados_error":
        barras = ax.bar(
            x,
            valores,
            width=0.58,
            color="coral",
            edgecolor="black",
            linewidth=0.7,
            hatch="//",
            label=str(configuracion["leyenda"]),
            zorder=3,
        )
        ax.axhline(
            CRITERIO_MAX_DEG,
            color="red",
            linestyle="--",
            linewidth=1.3,
            alpha=0.75,
            label=f"Criterio máximo: {CRITERIO_MAX_DEG:.0f}°",
            zorder=2,
        )

        maximo_datos = max(valores, default=0.0)
        desplazamiento = max(maximo_datos * 0.025, 0.12)
        for barra, valor in zip(barras, valores):
            ax.text(
                barra.get_x() + barra.get_width() / 2,
                valor + desplazamiento,
                f"{valor:.1f}°",
                ha="center",
                va="bottom",
                fontsize=9,
            )

        maximo = max(maximo_datos, CRITERIO_MAX_DEG)
        ax.set_ylim(0, maximo * 1.28)
    else:
        ax.plot(
            x,
            valores,
            marker="o",
            linewidth=2,
            markersize=7,
            color="coral",
            label=str(configuracion["leyenda"]),
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
        for posicion, valor in zip(x, valores):
            ax.annotate(
                f"{valor:.1f}°",
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
    ax.set_ylabel(str(configuracion["ylabel"]), fontsize=11)
    ax.set_title("Giro completo de 360°: robot físico", fontsize=14, pad=16)
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
        ruta = os.path.join(SCRIPT_DIR, f"giro_deriva_barras.{extension}")
        fig.savefig(ruta, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("Gráfico guardado: giro_deriva_barras.png / .pdf")


def imprimir_resumen(datos: list[ResultadoGiroReal]) -> None:
    print(
        f"\n{'Prueba':>7} {'Odom (°)':>11} {'Físico (°)':>12} "
        f"{'Desv. 360°':>13} {'Odom.-físico':>15}"
    )
    print("-" * 66)

    for dato in datos:
        print(
            f"{dato.prueba:>7} {dato.delta_odom:>11.2f} "
            f"{dato.angulo_fisico:>12.2f} "
            f"{dato.desviacion_fisica_deg:>11.2f}° "
            f"{dato.diferencia_odom_fisica_deg:>13.2f}°"
        )

    desviaciones = [dato.desviacion_fisica_deg for dato in datos]
    diferencias = [dato.diferencia_odom_fisica_deg for dato in datos]
    print(
        f"\nDesviación física media respecto a 360°: "
        f"{np.mean(desviaciones):.2f}°"
    )
    print(
        f"Diferencia media odometría-medición física: "
        f"{np.mean(diferencias):.2f}°"
    )
    seleccion = seleccionar_metrica(datos)
    print(f"Métrica utilizada en el gráfico: {seleccion['ylabel']}")


def main() -> None:
    print("\n" + "=" * 78)
    print("ANÁLISIS: giro de 360° con el robot físico")
    print("=" * 78)

    angulos_fisicos = leer_angulos_reales()
    datos = leer_resultados(angulos_fisicos)
    if not datos:
        print("Sin datos válidos para analizar.")
        return

    imprimir_resumen(datos)
    generar_latex(datos)
    generar_grafico(datos)

    print("\nArchivos generados:")
    print("  - tabla_odom_giro_real.tex")
    print("  - giro_deriva_barras.png / .pdf")


if __name__ == "__main__":
    main()