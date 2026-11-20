#!/usr/bin/env python3
import argparse
import csv
import os
import statistics
import sys

import matplotlib.pyplot as plt
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--t-bloqueo-ini", type=float, default=20.0)
    parser.add_argument("--t-bloqueo-fin", type=float, default=40.0)
    args = parser.parse_args()

    csv_path = os.path.join(SCRIPT_DIR, "bloqueo_lidar.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: no se encuentra {csv_path}")
        sys.exit(1)

    rows = []
    with open(csv_path) as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append({
                "t": float(r["t_rel"]),
                "n_tot": int(r["n_total"]),
                "n_val": int(r["n_validos"]),
                "n_cerca": int(r["n_muy_cerca"]),
                "mediana": float(r["mediana_range"]),
            })

    if not rows:
        print("ERROR: CSV vacío"); sys.exit(1)

    fases = {
        "Pre-bloqueo (0-{}s)".format(int(args.t_bloqueo_ini)):
            [r for r in rows if r["t"] < args.t_bloqueo_ini],
        "Bloqueado ({}-{}s)".format(int(args.t_bloqueo_ini), int(args.t_bloqueo_fin)):
            [r for r in rows if args.t_bloqueo_ini <= r["t"] < args.t_bloqueo_fin],
        "Post-bloqueo ({}-{}s)".format(int(args.t_bloqueo_fin), int(rows[-1]["t"])):
            [r for r in rows if r["t"] >= args.t_bloqueo_fin],
    }

    print()
    print("-" * 78)
    print(f"{'Fase':<28} {'%Válidos':>10} {'%MuyCerca':>11} {'MedianaR(m)':>14}")
    print("-" * 78)

    metricas = []
    for nombre, r_fase in fases.items():
        if not r_fase:
            metricas.append({"nombre": nombre, "validos_pct": 0, "cerca_pct": 0, "med": 0})
            continue
        n_tot_avg = statistics.mean([r["n_tot"] for r in r_fase])
        n_val_avg = statistics.mean([r["n_val"] for r in r_fase])
        n_cerca_avg = statistics.mean([r["n_cerca"] for r in r_fase])
        med_avg = statistics.mean([r["mediana"] for r in r_fase if r["mediana"] > 0])
        validos_pct = 100 * n_val_avg / n_tot_avg if n_tot_avg > 0 else 0
        cerca_pct = 100 * n_cerca_avg / n_tot_avg if n_tot_avg > 0 else 0

        print(f"{nombre:<28} {validos_pct:>10.1f} {cerca_pct:>11.1f} {med_avg:>14.3f}")

        metricas.append({
            "nombre": nombre,
            "validos_pct": validos_pct,
            "cerca_pct": cerca_pct,
            "med": med_avg,
        })

    print("-" * 78)

    pre = metricas[0]
    blq = metricas[1]
    post = metricas[2]

    delta_cerca = blq["cerca_pct"] - pre["cerca_pct"]
    delta_validos = blq["validos_pct"] - pre["validos_pct"]
    recupera = abs(post["validos_pct"] - pre["validos_pct"]) < 10

    print()
    if delta_cerca > 20 or delta_validos < -10:
        print(f"  ✓ DETECTADO: %muy_cerca subió {delta_cerca:+.1f}% durante bloqueo")
    else:
        print(f"  ⚠ NO DETECTADO claramente (Δ%cerca = {delta_cerca:+.1f})")

    if recupera:
        print(f"  ✓ RECUPERACIÓN: %válidos volvió a {post['validos_pct']:.1f}% (pre era {pre['validos_pct']:.1f}%)")
    else:
        print(f"  ⚠ Recuperación parcial: {post['validos_pct']:.1f}% vs pre {pre['validos_pct']:.1f}%")

    lineas = [
        "% Tabla del test de bloqueo intencional del LIDAR",
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Fase & Válidos (\\%) & Muy cerca $<$30\\,cm (\\%) & Mediana (m) \\\\",
        "\\midrule",
    ]
    for m in metricas:
        lineas.append(f"{m['nombre']} & {m['validos_pct']:.1f} & "
                      f"{m['cerca_pct']:.1f} & {m['med']:.3f} \\\\")
    lineas.append("\\bottomrule")
    lineas.append("\\end{tabular}")
    tex_path = os.path.join(SCRIPT_DIR, "tabla_bloqueo_lidar.tex")
    with open(tex_path, "w") as f:
        f.write("\n".join(lineas))
    print(f"\n  LaTeX guardada en: {tex_path}")

    fig, ax = plt.subplots(figsize=(10, 5))
    ts = [r["t"] for r in rows]

    pct_val = [100 * r["n_val"] / r["n_tot"] if r["n_tot"] > 0 else 0 for r in rows]
    pct_cerca = [100 * r["n_cerca"] / r["n_tot"] if r["n_tot"] > 0 else 0 for r in rows]

    ax.plot(ts, pct_val, color="steelblue", label="% válidos", linewidth=1.2)
    ax.plot(ts, pct_cerca, color="coral", label="% muy cerca (<30 cm)", linewidth=1.2)

    ax.axvspan(args.t_bloqueo_ini, args.t_bloqueo_fin,
               alpha=0.2, color="red", label="Bloqueo activo")

    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("Porcentaje (%)")
    ax.set_title("Evolución temporal del LIDAR ante inyección de fallo (bloqueo)")
    ax.legend(loc="best", fontsize=10)
    ax.grid(alpha=0.3)
    ax.set_ylim([0, 105])

    plt.tight_layout()
    for ext in ("pdf", "png"):
        path = os.path.join(SCRIPT_DIR, f"bloqueo_lidar_temporal.{ext}")
        plt.savefig(path, dpi=150)
    print(f"  Figura guardada: bloqueo_lidar_temporal.pdf / .png")
    plt.close()

    resumen = [
        f"Test de bloqueo intencional del LIDAR",
        f"=" * 60,
        f"",
    ]
    for m in metricas:
        resumen.append(f"  {m['nombre']}:")
        resumen.append(f"    %válidos    : {m['validos_pct']:.1f}%")
        resumen.append(f"    %muy_cerca  : {m['cerca_pct']:.1f}%")
        resumen.append(f"    mediana(m)  : {m['med']:.3f}")
        resumen.append("")
    resumen.append(f"  Detección del bloqueo: {'SI' if delta_cerca > 20 or delta_validos < -10 else 'NO'}")
    resumen.append(f"  Recuperación post-fallo: {'COMPLETA' if recupera else 'PARCIAL'}")

    with open(os.path.join(SCRIPT_DIR, "bloqueo_lidar_resumen.txt"), "w") as f:
        f.write("\n".join(resumen))

if __name__ == "__main__":
    main()