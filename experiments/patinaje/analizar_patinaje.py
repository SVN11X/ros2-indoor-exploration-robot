#!/usr/bin/env python3
import csv
import math
import os
import statistics
import sys

import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    csv_path = os.path.join(SCRIPT_DIR, "patinaje.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: no se encuentra {csv_path}")
        sys.exit(1)

    rows = []
    with open(csv_path) as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append({k: float(v) for k, v in r.items()})

    if not rows:
        print("ERROR: CSV vacío"); sys.exit(1)

    ts = [r["t_rel"] for r in rows]
    ox = [r["odom_x"] for r in rows]
    oy = [r["odom_y"] for r in rows]
    mx = [r["map_x"] for r in rows]
    my = [r["map_y"] for r in rows]
    errs = [r["err"] for r in rows]

    err_max = max(errs)
    err_max_idx = errs.index(err_max)
    err_max_t = ts[err_max_idx]
    err_final = errs[-1]
    err_inicial = errs[0]

    odom_dist_total = sum(
        math.sqrt((ox[i] - ox[i-1]) ** 2 + (oy[i] - oy[i-1]) ** 2)
        for i in range(1, len(ox))
    )
    map_dist_total = sum(
        math.sqrt((mx[i] - mx[i-1]) ** 2 + (my[i] - my[i-1]) ** 2)
        for i in range(1, len(mx))
    )

    print()
    print("-" * 70)
    print(f"  Duración total          : {ts[-1]:.1f} s")
    print(f"  Muestras                : {len(rows)}")
    print(f"  Error inicial           : {err_inicial:.3f} m")
    print(f"  Error final             : {err_final:.3f} m")
    print(f"  Error máximo            : {err_max:.3f} m  (en t={err_max_t:.1f} s)")
    print(f"  Distancia recorrida odom: {odom_dist_total:.3f} m (lo que cree odom)")
    print(f"  Distancia recorrida map : {map_dist_total:.3f} m (lo que SLAM ve)")
    print("-" * 70)

    if err_max > 0.1:
        print(f"\n  ✓ Demostrado: odom y map divergieron hasta {err_max:.2f} m")
        print(f"    → SLAM Toolbox corrigió pose vía scan matching contra LIDAR")
    else:
        print(f"\n  ⚠ Discrepancia máxima muy baja ({err_max:.3f} m)")
        print(f"    Repetir el test induciendo más patinaje manual")

    pct_mentira = 100 * (odom_dist_total - map_dist_total) / odom_dist_total if odom_dist_total > 0 else 0
    lineas = [
        "% Tabla del test de patinaje (discrepancia odom vs SLAM)",
        "\\begin{tabular}{lr}",
        "\\toprule",
        "Métrica & Valor \\\\",
        "\\midrule",
        f"Duración del experimento     & \\SI{{{ts[-1]:.0f}}}{{\\second}} \\\\",
        f"Muestras                     & {len(rows)} \\\\",
        f"Error inicial $|odom-map|$   & \\SI{{{err_inicial:.3f}}}{{\\meter}} \\\\",
        f"Error final $|odom-map|$     & \\SI{{{err_final:.3f}}}{{\\meter}} \\\\",
        f"Error máximo $|odom-map|$    & \\SI{{{err_max:.3f}}}{{\\meter}} \\\\",
        f"Distancia integrada (odom)   & \\SI{{{odom_dist_total:.3f}}}{{\\meter}} \\\\",
        f"Distancia integrada (map)    & \\SI{{{map_dist_total:.3f}}}{{\\meter}} \\\\",
        f"Sobre-estimación odom (\\%)  & {abs(pct_mentira):.1f}\\,\\% \\\\",
        "\\bottomrule",
        "\\end{tabular}",
    ]
    tex_path = os.path.join(SCRIPT_DIR, "tabla_patinaje.tex")
    with open(tex_path, "w") as f:
        f.write("\n".join(lineas))
    print(f"\n  LaTeX guardada en: {tex_path}")

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.plot(ox, oy, color="coral", label="Odometría (encoders)", linewidth=1.5, marker="o", markersize=3)
    ax.plot(mx, my, color="steelblue", label="SLAM (map→base_link)", linewidth=1.5, marker="s", markersize=3)
    ax.scatter([ox[0]], [oy[0]], color="green", s=80, zorder=5, label="Inicio")
    ax.scatter([ox[-1]], [oy[-1]], color="coral", s=80, marker="X", zorder=5,
               label=f"Fin odom ({ox[-1]:.2f}, {oy[-1]:.2f})")
    ax.scatter([mx[-1]], [my[-1]], color="steelblue", s=80, marker="X", zorder=5,
               label=f"Fin map ({mx[-1]:.2f}, {my[-1]:.2f})")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title("Trayectoria estimada: odometría pura vs SLAM con LIDAR")
    ax.legend(loc="best", fontsize=10)
    ax.grid(alpha=0.3)
    ax.axis("equal")
    plt.tight_layout()
    for ext in ("pdf", "png"):
        path = os.path.join(SCRIPT_DIR, f"patinaje_trayectorias.{ext}")
        plt.savefig(path, dpi=150)
    print(f"  Figura guardada: patinaje_trayectorias.pdf / .png")
    plt.close()

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(ts, errs, color="firebrick", linewidth=1.5)
    ax.fill_between(ts, 0, errs, alpha=0.2, color="firebrick")
    ax.axhline(err_max, color="black", linestyle="--", alpha=0.5,
               label=f"Máx: {err_max:.3f} m a t={err_max_t:.0f} s")
    ax.set_xlabel("Tiempo (s)")
    ax.set_ylabel("$||\\,$pose$_{odom}$ - pose$_{map}\\,||$ (m)")
    ax.set_title("Discrepancia odometría vs SLAM en el tiempo")
    ax.legend(fontsize=10)
    ax.grid(alpha=0.3)
    plt.tight_layout()
    for ext in ("pdf", "png"):
        path = os.path.join(SCRIPT_DIR, f"patinaje_error.{ext}")
        plt.savefig(path, dpi=150)
    print(f"  Figura guardada: patinaje_error.pdf / .png")
    plt.close()

    resumen = [
        f"Test de patinaje (odom vs SLAM)",
        f"=" * 60,
        f"",
        f"Duración total           : {ts[-1]:.1f} s",
        f"Muestras                 : {len(rows)}",
        f"Error inicial            : {err_inicial:.3f} m",
        f"Error final              : {err_final:.3f} m",
        f"Error máximo             : {err_max:.3f} m  (t = {err_max_t:.1f} s)",
        f"Distancia odom (integ.)  : {odom_dist_total:.3f} m",
        f"Distancia map (integ.)   : {map_dist_total:.3f} m",
        f"Sobre-estimación odom    : {abs(pct_mentira):.1f} %",
        f"",
        f"Interpretación:",
        f"  - 'odom' integra ticks de encoder; no detecta cuando el robot",
        f"    es transportado o patina. Acumula error.",
        f"  - 'map' es corregido por SLAM Toolbox mediante scan matching",
        f"    contra el mapa generado por el LIDAR. Mantiene la pose real.",
        f"  - La discrepancia |odom-map| cuantifica cuánto miente la",
        f"    odometría sola y cuánto corrige SLAM con el LIDAR.",
    ]
    with open(os.path.join(SCRIPT_DIR, "patinaje_resumen.txt"), "w") as f:
        f.write("\n".join(resumen))

if __name__ == "__main__":
    main()