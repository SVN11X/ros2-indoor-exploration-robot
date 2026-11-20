#!/usr/bin/env python3
import csv
import math
import os
import statistics
import sys

import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SPEC_FREQ_MIN = 5.5
SPEC_FREQ_MAX = 10.0
SPEC_RES_DEG_NOM = 1.0
UART_LIMIT_SAMPLES = 2300

def cargar_csv(path):
    rows = []
    with open(path) as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append({
                "t": float(r["t_recv"]),
                "n_tot": int(r["n_total"]),
                "n_val": int(r["n_validos"]),
                "n_inf": int(r["n_inf"]),
                "span": float(r["span_rad"]),
                "ainc": float(r["ang_inc"]),
                "rmin": float(r["range_min_obs"]),
                "rmax": float(r["range_max_obs"]),
            })
    return rows

def metricas_prueba(rows):
    ts = [r["t"] for r in rows]
    periods = [ts[i+1] - ts[i] for i in range(len(ts) - 1)]
    mp = statistics.mean(periods)
    sp = statistics.stdev(periods) if len(periods) > 1 else 0.0

    n_tot = [r["n_tot"] for r in rows]
    n_val = [r["n_val"] for r in rows]
    spans = [r["span"] for r in rows]
    aincs = [r["ainc"] for r in rows]

    return {
        "freq_hz": 1.0 / mp,
        "periodo_ms": mp * 1000,
        "jitter_pct": 100 * sp / mp,
        "n_tot_mean": statistics.mean(n_tot),
        "n_val_mean": statistics.mean(n_val),
        "n_val_std": statistics.stdev(n_val) if len(n_val) > 1 else 0.0,
        "span_deg_mean": math.degrees(statistics.mean(spans)),
        "res_deg_mean": math.degrees(statistics.mean(aincs)),
        "samples_per_sec": statistics.mean(n_tot) / mp,
        "n_scans": len(rows),
    }

def main():
    pruebas = []
    for n in range(1, 11):
        path = os.path.join(SCRIPT_DIR, f"calidad_lidar_{n}.csv")
        if not os.path.exists(path):
            continue
        rows = cargar_csv(path)
        if len(rows) < 5:
            print(f"AVISO: {path} tiene muy pocos scans, se omite")
            continue
        m = metricas_prueba(rows)
        m["prueba"] = n
        pruebas.append(m)

    if not pruebas:
        print(f"ERROR: no se encontraron archivos calidad_lidar_*.csv en {SCRIPT_DIR}")
        sys.exit(1)

    print()
    print("-" * 100)
    print(f"{'#':>3} {'Freq(Hz)':>9} {'Periodo(ms)':>12} {'Jitter(%)':>10} "
          f"{'Puntos':>8} {'Válidos':>9} {'Span(°)':>8} {'Res(°)':>7} {'Sam/s':>7}")
    print("-" * 100)
    for p in pruebas:
        print(f"{p['prueba']:>3} {p['freq_hz']:>9.2f} {p['periodo_ms']:>12.1f} "
              f"{p['jitter_pct']:>10.1f} {p['n_tot_mean']:>8.0f} "
              f"{p['n_val_mean']:>9.0f} {p['span_deg_mean']:>8.1f} "
              f"{p['res_deg_mean']:>7.3f} {p['samples_per_sec']:>7.0f}")
    print("-" * 100)

    freq_all = [p["freq_hz"] for p in pruebas]
    n_val_all = [p["n_val_mean"] for p in pruebas]
    jit_all = [p["jitter_pct"] for p in pruebas]
    samp_all = [p["samples_per_sec"] for p in pruebas]

    freq_mean = statistics.mean(freq_all)
    freq_std = statistics.stdev(freq_all) if len(freq_all) > 1 else 0.0
    nval_mean = statistics.mean(n_val_all)
    nval_std = statistics.stdev(n_val_all) if len(n_val_all) > 1 else 0.0
    jit_mean = statistics.mean(jit_all)
    samp_mean = statistics.mean(samp_all)
    util_pct = 100 * samp_mean / UART_LIMIT_SAMPLES

    print(f"\n  Frecuencia media     : {freq_mean:.2f} ± {freq_std:.2f} Hz")
    print(f"  Puntos válidos medios: {nval_mean:.0f} ± {nval_std:.0f}")
    print(f"  Jitter medio         : {jit_mean:.1f}%")
    print(f"  Samples/s medios     : {samp_mean:.0f} ({util_pct:.0f}% del UART 115200)")

    print(f"\n  Veredicto SLAM 2D    : ", end="")
    issues = []
    if not (SPEC_FREQ_MIN <= freq_mean <= SPEC_FREQ_MAX + 1):
        issues.append("frecuencia fuera de rango A1")
    if nval_mean < 100:
        issues.append("pocos puntos válidos")
    if jit_mean > 25:
        issues.append("jitter alto")
    if pruebas[0]["span_deg_mean"] < 350:
        issues.append("cobertura angular incompleta")

    if not issues:
        print("✓ APTO")
    else:
        print(f"⚠ revisar: {', '.join(issues)}")

    lineas = [
        "% Tabla de caracterización experimental del RPLidar A1M8",
        "% Generada por test/calidad_lidar/analizar_calidad_lidar.py",
        "\\begin{tabular}{rrrrrrrr}",
        "\\toprule",
        "\\# & Freq.\\ (Hz) & Periodo (ms) & Jitter (\\%) & "
        "Puntos & Válidos & Span (°) & Sam/s \\\\",
        "\\midrule",
    ]
    for p in pruebas:
        lineas.append(
            f"{p['prueba']} & {p['freq_hz']:.2f} & {p['periodo_ms']:.1f} & "
            f"{p['jitter_pct']:.1f} & {p['n_tot_mean']:.0f} & "
            f"{p['n_val_mean']:.0f} & {p['span_deg_mean']:.1f} & "
            f"{p['samples_per_sec']:.0f} \\\\"
        )
    lineas.append("\\midrule")
    lineas.append(
        f"$\\overline{{x}}$ & {freq_mean:.2f} & "
        f"{statistics.mean([p['periodo_ms'] for p in pruebas]):.1f} & "
        f"{jit_mean:.1f} & "
        f"{statistics.mean([p['n_tot_mean'] for p in pruebas]):.0f} & "
        f"{nval_mean:.0f} & "
        f"{statistics.mean([p['span_deg_mean'] for p in pruebas]):.1f} & "
        f"{samp_mean:.0f} \\\\"
    )
    lineas.append(
        f"$\\sigma$ & {freq_std:.2f} & "
        f"{statistics.stdev([p['periodo_ms'] for p in pruebas]) if len(pruebas) > 1 else 0:.1f} & "
        f"{statistics.stdev(jit_all) if len(jit_all) > 1 else 0:.1f} & "
        f"--- & {nval_std:.0f} & --- & "
        f"{statistics.stdev(samp_all) if len(samp_all) > 1 else 0:.0f} \\\\"
    )
    lineas.append("\\bottomrule")
    lineas.append("\\end{tabular}")
    tex_path = os.path.join(SCRIPT_DIR, "tabla_calidad_lidar.tex")
    with open(tex_path, "w") as f:
        f.write("\n".join(lineas))
    print(f"\n  LaTeX guardada en: {tex_path}")

    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    pruebas_num = [p["prueba"] for p in pruebas]
    axes[0].bar(pruebas_num, freq_all, color="steelblue", zorder=3)
    axes[0].axhline(SPEC_FREQ_MIN, color="red", linestyle="--", alpha=0.5,
                    label=f"Mín. spec ({SPEC_FREQ_MIN} Hz)")
    axes[0].axhline(SPEC_FREQ_MAX, color="red", linestyle="--", alpha=0.5,
                    label=f"Máx. spec ({SPEC_FREQ_MAX} Hz)")
    axes[0].set_xlabel("Captura #")
    axes[0].set_ylabel("Frecuencia (Hz)")
    axes[0].set_title("Tasa de barrido del LIDAR por captura")
    axes[0].set_xticks(pruebas_num)
    axes[0].grid(axis="y", alpha=0.3, zorder=0)
    axes[0].legend(fontsize=9)

    axes[1].bar(pruebas_num, n_val_all, color="coral", zorder=3)
    axes[1].axhline(100, color="red", linestyle="--", alpha=0.5,
                    label="Mín. SLAM (100 pts)")
    axes[1].set_xlabel("Captura #")
    axes[1].set_ylabel("Puntos válidos por scan")
    axes[1].set_title("Densidad angular por captura")
    axes[1].set_xticks(pruebas_num)
    axes[1].grid(axis="y", alpha=0.3, zorder=0)
    axes[1].legend(fontsize=9)

    plt.tight_layout()
    for ext in ("pdf", "png"):
        path = os.path.join(SCRIPT_DIR, f"calidad_lidar_freq.{ext}")
        plt.savefig(path, dpi=150)
    print(f"  Figura guardada: calidad_lidar_freq.pdf / .png")
    plt.close()

    resumen = [
        f"Caracterización del LIDAR RPLidar A1M8",
        f"=" * 60,
        f"Pruebas analizadas: {len(pruebas)}",
        f"",
        f"Frecuencia       : {freq_mean:.2f} ± {freq_std:.2f} Hz",
        f"Puntos válidos   : {nval_mean:.0f} ± {nval_std:.0f}",
        f"Jitter temporal  : {jit_mean:.1f} %",
        f"Samples/s        : {samp_mean:.0f}",
        f"Utilización UART : {util_pct:.0f} %",
        f"",
        f"Span angular     : {pruebas[0]['span_deg_mean']:.1f} °",
        f"Resolución       : {pruebas[0]['res_deg_mean']:.3f} ° / punto",
        f"",
        f"Veredicto: {'APTO para SLAM 2D' if not issues else '⚠ ' + ', '.join(issues)}",
    ]
    with open(os.path.join(SCRIPT_DIR, "calidad_lidar_resumen.txt"), "w") as f:
        f.write("\n".join(resumen))

if __name__ == "__main__":
    main()