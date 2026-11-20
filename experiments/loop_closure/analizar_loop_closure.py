#!/usr/bin/env python3
import csv
import math
import os
import statistics
import sys

import matplotlib.pyplot as plt

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def main():
    csv_path = os.path.join(SCRIPT_DIR, "loop_closure.csv")
    if not os.path.exists(csv_path):
        print(f"ERROR: no se encuentra {csv_path}")
        sys.exit(1)

    rows = []
    with open(csv_path) as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows.append({k: float(v) for k, v in r.items()})

    if len(rows) < 10:
        print(f"ERROR: muy pocas muestras ({len(rows)})")
        sys.exit(1)

    ts = [r["t_rel"] for r in rows]
    ox = [r["odom_x"] for r in rows]
    oy = [r["odom_y"] for r in rows]
    oyaw = [r["odom_yaw"] for r in rows]
    mx = [r["map_x"] for r in rows]
    my = [r["map_y"] for r in rows]
    myaw = [r["map_yaw"] for r in rows]

    map_dist = sum(
        math.sqrt((mx[i] - mx[i-1]) ** 2 + (my[i] - my[i-1]) ** 2)
        for i in range(1, len(mx))
    )
    odom_dist = sum(
        math.sqrt((ox[i] - ox[i-1]) ** 2 + (oy[i] - oy[i-1]) ** 2)
        for i in range(1, len(ox))
    )

    err_map = math.sqrt((mx[-1] - mx[0]) ** 2 + (my[-1] - my[0]) ** 2)
    err_odom = math.sqrt((ox[-1] - ox[0]) ** 2 + (oy[-1] - oy[0]) ** 2)

    err_yaw_map = abs(myaw[-1] - myaw[0])
    if err_yaw_map > math.pi:
        err_yaw_map = 2 * math.pi - err_yaw_map
    err_yaw_deg = math.degrees(err_yaw_map)

    err_pct_map = 100 * err_map / map_dist if map_dist > 0 else 0
    err_pct_odom = 100 * err_odom / odom_dist if odom_dist > 0 else 0

    print()
    print("-" * 65)
    print(f"  Duración del recorrido       : {ts[-1]:.1f} s")
    print(f"  Muestras registradas         : {len(rows)}")
    print()
    print(f"  Distancia integrada (map)    : {map_dist:.3f} m  (referencia fiable)")
    print(f"  Distancia integrada (odom)   : {odom_dist:.3f} m  (encoders)")
    print()
    print(f"  Error de cierre POSICIÓN (map)  : {err_map:.3f} m  → {err_pct_map:.2f}% del recorrido")
    print(f"  Error de cierre POSICIÓN (odom) : {err_odom:.3f} m  → {err_pct_odom:.2f}% del recorrido")
    print(f"  Error de cierre ORIENTACIÓN(map): {err_yaw_deg:.2f}°")
    print("-" * 65)

    print()
    if err_pct_map < 5 and err_yaw_deg < 5:
        print(f"  ✓ APTO  (error < 5% en distancia y < 5° en orientación)")
    elif err_pct_map < 10:
        print(f"  ⚠ ACEPTABLE para mapeo básico, no para navegación de precisión")
    else:
        print(f"  ✗ Error alto. Revisar calibración o trayectoria")

    lineas = [
        "% Tabla del test de cierre de loop (loop closure)",
        "\\begin{tabular}{lr}",
        "\\toprule",
        "Métrica & Valor \\\\",
        "\\midrule",
        f"Duración del recorrido          & \\SI{{{ts[-1]:.0f}}}{{\\second}} \\\\",
        f"Distancia recorrida (SLAM)      & \\SI{{{map_dist:.3f}}}{{\\meter}} \\\\",
        f"Distancia recorrida (odom)      & \\SI{{{odom_dist:.3f}}}{{\\meter}} \\\\",
        f"Error de cierre — posición (SLAM)  & \\SI{{{err_map:.3f}}}{{\\meter}} ({err_pct_map:.2f}\\,\\%) \\\\",
        f"Error de cierre — posición (odom)  & \\SI{{{err_odom:.3f}}}{{\\meter}} ({err_pct_odom:.2f}\\,\\%) \\\\",
        f"Error de cierre — orientación (SLAM) & \\SI{{{err_yaw_deg:.2f}}}{{\\degree}} \\\\",
        "\\bottomrule",
        "\\end{tabular}",
    ]
    tex_path = os.path.join(SCRIPT_DIR, "tabla_loop_closure.tex")
    with open(tex_path, "w") as f:
        f.write("\n".join(lineas))
    print(f"\n  LaTeX guardada en: {tex_path}")

    fig, ax = plt.subplots(figsize=(8, 7))
    ax.plot(mx, my, color="steelblue", linewidth=1.5, label="Trayectoria SLAM (map)", zorder=3)
    ax.plot(ox, oy, color="coral", linewidth=1.5, alpha=0.7, label="Trayectoria odom", zorder=2)
    ax.scatter([mx[0]], [my[0]], color="green", s=150, marker="o", zorder=5,
               label=f"Inicio P0 ({mx[0]:.2f}, {my[0]:.2f})", edgecolors="black", linewidths=1.5)
    ax.scatter([mx[-1]], [my[-1]], color="red", s=150, marker="X", zorder=5,
               label=f"Fin Pf SLAM ({mx[-1]:.2f}, {my[-1]:.2f})", edgecolors="black", linewidths=1.5)
    ax.scatter([ox[-1]], [oy[-1]], color="orange", s=120, marker="s", zorder=4,
               label=f"Fin Pf odom ({ox[-1]:.2f}, {oy[-1]:.2f})", edgecolors="black", linewidths=1.5)

    ax.plot([mx[0], mx[-1]], [my[0], my[-1]], color="red", linestyle=":", alpha=0.5,
            label=f"Error cierre: {err_map:.3f} m ({err_pct_map:.1f}%)")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(f"Test de cierre de loop — recorrido {map_dist:.2f} m")
    ax.legend(loc="best", fontsize=9)
    ax.grid(alpha=0.3)
    ax.axis("equal")
    plt.tight_layout()
    for ext in ("pdf", "png"):
        path = os.path.join(SCRIPT_DIR, f"loop_closure_trayectoria.{ext}")
        plt.savefig(path, dpi=150)
    print(f"  Figura guardada: loop_closure_trayectoria.pdf / .png")
    plt.close()

    resumen = [
        f"Test de cierre de loop (loop closure)",
        f"=" * 60,
        f"",
        f"Duración             : {ts[-1]:.1f} s",
        f"Distancia (SLAM)     : {map_dist:.3f} m",
        f"Distancia (odom)     : {odom_dist:.3f} m",
        f"",
        f"Error de cierre:",
        f"  Posición (SLAM)    : {err_map:.3f} m  ({err_pct_map:.2f}%)",
        f"  Posición (odom)    : {err_odom:.3f} m  ({err_pct_odom:.2f}%)",
        f"  Orientación (SLAM) : {err_yaw_deg:.2f}°",
        f"",
        f"Criterio estándar SLAM consumer: < 5% en distancia, < 5° en yaw",
        f"Veredicto: {'APTO' if err_pct_map < 5 and err_yaw_deg < 5 else ('ACEPTABLE' if err_pct_map < 10 else 'REVISAR')}",
    ]
    with open(os.path.join(SCRIPT_DIR, "loop_closure_resumen.txt"), "w") as f:
        f.write("\n".join(resumen))

if __name__ == "__main__":
    main()