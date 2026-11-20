#!/usr/bin/env python3
"""
Analiza las cinco pruebas de trayectoria rectilínea ejecutadas con el robot
físico.

Entradas esperadas, en la misma carpeta del script:
    prueba_recta_1.log
    ...
    prueba_recta_5.log
    distancias_reales.txt

Salidas:
    tabla_odom_recta_real.tex
    odom_error_barras.png
    odom_error_barras.pdf

Criterio para evitar gráficos vacíos:
1. Se grafica el error entre la odometría y la medición física.
2. Si ese error es 0 % en todas las pruebas, se grafica la desviación de la
   distancia física respecto de los 2 m teóricos.
3. Si ambas métricas son 0 %, se muestran las distancias físicas obtenidas y
   una línea de referencia en 2 m.

Este archivo representa únicamente pruebas del robot físico. No contiene
valores fijos ni resultados provenientes de Gazebo.
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
DIST_FILE = os.path.join(SCRIPT_DIR, "distancias_reales.txt")
N_PRUEBAS = 5
DIST_TEORICA = 2.00
CRITERIO_MAX_PCT = 5.0
TOL_CASI_CERO = 1e-6
TOL_IGUALES = 0.005


@dataclass(frozen=True)
class ResultadoRectaReal:
    prueba: int
    dist_teorica: float
    dist_odom: float
    dist_fisica: float
    error_odom_fisica_pct: float
    desviacion_objetivo_pct: float


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


def leer_distancias_reales() -> list[float]:
    if not os.path.exists(DIST_FILE):
        print(f"ERROR: no se encuentra '{DIST_FILE}'.")
        print("Crea el archivo con una distancia física por línea, en metros.")
        print("Ejemplo:")
        print("  1.958")
        print("  1.963")
        sys.exit(1)

    valores: list[float] = []
    with open(DIST_FILE, encoding="utf-8") as archivo:
        for numero_linea, linea in enumerate(archivo, start=1):
            linea = linea.strip()
            if not linea or linea.startswith("#"):
                continue
            try:
                valores.append(float(linea))
            except ValueError:
                print(
                    f"AVISO: línea {numero_linea} no numérica omitida en "
                    f"{os.path.basename(DIST_FILE)}: {linea!r}"
                )

    if len(valores) < N_PRUEBAS:
        print(
            f"ERROR: '{DIST_FILE}' contiene {len(valores)} mediciones; "
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


def leer_resultados(distancias_fisicas: list[float]) -> list[ResultadoRectaReal]:
    resultados: list[ResultadoRectaReal] = []

    for numero, dist_fisica in enumerate(distancias_fisicas, start=1):
        ruta = os.path.join(SCRIPT_DIR, f"prueba_recta_{numero}.log")
        if not os.path.exists(ruta):
            print(f"AVISO: no se encuentra {ruta}; se omite la prueba {numero}.")
            continue

        fila = leer_log_numerico(ruta)
        if "dist_odom" not in fila:
            print(f"ERROR: falta 'dist_odom' en {ruta}; se omite la prueba {numero}.")
            continue

        dist_teorica = fila.get("dist_teorica", DIST_TEORICA)
        dist_odom = fila["dist_odom"]

        error_odom_fisica_pct = (
            abs(dist_odom - dist_fisica) / abs(dist_fisica) * 100.0
            if abs(dist_fisica) > TOL_CASI_CERO
            else 0.0
        )
        desviacion_objetivo_pct = (
            abs(dist_fisica - dist_teorica) / abs(dist_teorica) * 100.0
            if abs(dist_teorica) > TOL_CASI_CERO
            else 0.0
        )

        resultados.append(
            ResultadoRectaReal(
                prueba=numero,
                dist_teorica=dist_teorica,
                dist_odom=dist_odom,
                dist_fisica=dist_fisica,
                error_odom_fisica_pct=error_odom_fisica_pct,
                desviacion_objetivo_pct=desviacion_objetivo_pct,
            )
        )

    return resultados


def seleccionar_metrica(
    datos: list[ResultadoRectaReal],
) -> dict[str, object]:
    errores = [dato.error_odom_fisica_pct for dato in datos]
    desviaciones = [dato.desviacion_objetivo_pct for dato in datos]
    distancias = [dato.dist_fisica for dato in datos]

    if not todos_casi_cero(errores):
        return {
            "modo": "porcentaje",
            "valores": errores,
            "ylabel": "Error de odometría respecto a la medición física (%)",
            "leyenda": "Robot físico: odometría vs. medición con cinta",
        }

    if not todos_casi_cero(desviaciones):
        return {
            "modo": "porcentaje",
            "valores": desviaciones,
            "ylabel": "Desviación de la medición física respecto a 2 m (%)",
            "leyenda": "Robot físico: recorrido medido vs. 2 m teóricos",
        }

    return {
        "modo": "distancia",
        "valores": distancias,
        "ylabel": "Distancia física recorrida (m)",
        "leyenda": "Robot físico: distancia medida",
    }


def generar_latex(datos: list[ResultadoRectaReal]) -> None:
    errores = [dato.error_odom_fisica_pct for dato in datos]
    media = f"{np.mean(errores):.2f}" if errores else "N/D"

    lineas = [
        "% Resultados de la prueba rectilínea con el robot físico.",
        "% Filas listas para incorporar en la tabla del capítulo de resultados.",
    ]

    datos_por_prueba = {dato.prueba: dato for dato in datos}
    for numero in range(1, N_PRUEBAS + 1):
        dato = datos_por_prueba.get(numero)
        if dato is None:
            lineas.append(
                f"        {numero} & {DIST_TEORICA:.2f} & N/D & N/D & N/D \\\\"
            )
            continue

        lineas.append(
            f"        {numero} & {dato.dist_teorica:.2f} & "
            f"{dato.dist_odom:.3f} & {dato.dist_fisica:.3f} & "
            f"{dato.error_odom_fisica_pct:.2f}\\% \\\\"
        )

    lineas.append(
        f"        \\multicolumn{{4}}{{r}}{{\\textbf{{Error medio}}}} & "
        f"\\textbf{{{media}\\%}} \\\\"
    )

    ruta_salida = os.path.join(SCRIPT_DIR, "tabla_odom_recta_real.tex")
    with open(ruta_salida, "w", encoding="utf-8") as archivo:
        archivo.write("\n".join(lineas))
    print(f"LaTeX guardado en: {ruta_salida}")


def generar_grafico(datos: list[ResultadoRectaReal]) -> None:
    if not datos:
        print("AVISO: no hay datos físicos para graficar.")
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
            color="coral",
            edgecolor="black",
            linewidth=0.7,
            hatch="//",
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
            color="coral",
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
    ax.set_title("Trayectoria rectilínea de 2 m: robot físico", fontsize=14, pad=16)
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
        ruta = os.path.join(SCRIPT_DIR, f"odom_error_barras.{extension}")
        fig.savefig(ruta, dpi=180, bbox_inches="tight")
    plt.close(fig)
    print("Gráfico guardado: odom_error_barras.png / .pdf")


def imprimir_resumen(datos: list[ResultadoRectaReal]) -> None:
    print(
        f"\n{'Prueba':>7} {'Teórica (m)':>12} {'Odom (m)':>11} "
        f"{'Física (m)':>12} {'Error odom.':>13} {'Desv. 2 m':>12}"
    )
    print("-" * 76)

    for dato in datos:
        print(
            f"{dato.prueba:>7} {dato.dist_teorica:>12.3f} "
            f"{dato.dist_odom:>11.3f} {dato.dist_fisica:>12.3f} "
            f"{dato.error_odom_fisica_pct:>11.2f} % "
            f"{dato.desviacion_objetivo_pct:>10.2f} %"
        )

    errores = [dato.error_odom_fisica_pct for dato in datos]
    desviaciones = [dato.desviacion_objetivo_pct for dato in datos]
    print(f"\nError odométrico medio: {np.mean(errores):.2f} %")
    print(f"Desviación media respecto a 2 m: {np.mean(desviaciones):.2f} %")
    seleccion = seleccionar_metrica(datos)
    print(f"Métrica utilizada en el gráfico: {seleccion['ylabel']}")


def main() -> None:
    print("\n" + "=" * 78)
    print("ANÁLISIS: trayectoria rectilínea con el robot físico")
    print("=" * 78)

    distancias_fisicas = leer_distancias_reales()
    datos = leer_resultados(distancias_fisicas)
    if not datos:
        print("Sin datos válidos para analizar.")
        return

    imprimir_resumen(datos)
    generar_latex(datos)
    generar_grafico(datos)

    print("\nArchivos generados:")
    print("  - tabla_odom_recta_real.tex")
    print("  - odom_error_barras.png / .pdf")


if __name__ == "__main__":
    main()