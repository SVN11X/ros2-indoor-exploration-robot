#!/usr/bin/env python3
import csv
import os
import statistics
import sys

import matplotlib.pyplot as plt
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

def cargar_tasas(path):
    if not os.path.exists(path):
        return None
    rows = {}
    with open(path) as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            rows[r["topic"]] = {
                "freq": float(r["freq_hz"]),
                "p_mean": float(r["periodo_ms_mean"]),
                "p_std": float(r["periodo_ms_std"]),
                "p_min": float(r["periodo_ms_min"]),
                "p_max": float(r["periodo_ms_max"]),
                "n": int(r["n_msgs"]),
            }
    return rows

def cargar_termico(path):
    if not os.path.exists(path):
        return None
    rows = []
    with open(path) as f:
        rdr = csv.DictReader(f)
        for r in rdr:
            try:
                temp = float(r["temp_c"])
                load = float(r["load_1m"])
            except (KeyError, ValueError):
                continue
            ts = datetime.strptime(r["t_iso"], "%Y-%m-%dT%H:%M:%S")
            rows.append({"ts": ts, "temp": temp, "load": load})
    return rows

def main():
    base = cargar_tasas(os.path.join(SCRIPT_DIR, "stress_baseline.csv"))
    stre = cargar_tasas(os.path.join(SCRIPT_DIR, "stress_durante.csv"))
    term = cargar_termico(os.path.join(SCRIPT_DIR, "stress_termico.csv"))

    if base is None or stre is None:
        print("ERROR: faltan archivos stress_baseline.csv o stress_durante.csv")
        sys.exit(1)

    print()
    print("-" * 88)
    print(f"{'Topic':<10} {'Métrica':<22} {'Baseline':>12} {'Durante stress':>16} {'Δ%':>9}")
    print("-" * 88)

    deltas = {}
    for topic in ["/scan", "/odom"]:
        if topic not in base or topic not in stre:
            continue
        b = base[topic]; s = stre[topic]
        d_freq = 100 * (s["freq"] - b["freq"]) / b["freq"]
        d_jit = 100 * (s["p_std"] - b["p_std"]) / b["p_std"] if b["p_std"] > 0 else 0
        deltas[topic] = {"freq": d_freq, "jit": d_jit}

        print(f"{topic:<10} {'Frecuencia (Hz)':<22} {b['freq']:>12.2f} {s['freq']:>16.2f} {d_freq:>+8.1f}%")
        print(f"{topic:<10} {'Jitter (ms)':<22} {b['p_std']:>12.2f} {s['p_std']:>16.2f} {d_jit:>+8.1f}%")
        print(f"{topic:<10} {'Periodo min (ms)':<22} {b['p_min']:>12.2f} {s['p_min']:>16.2f} {'':>9}")
        print(f"{topic:<10} {'Periodo max (ms)':<22} {b['p_max']:>12.2f} {s['p_max']:>16.2f} {'':>9}")
        print()

    if term:
        loads = [r["load"] for r in term]
        temps = [r["temp"] for r in term]
        load_max = max(loads)
        temp_max = max(temps)
        load_baseline = statistics.median(loads[:3]) if len(loads) >= 3 else loads[0]
        temp_baseline = statistics.median(temps[:3]) if len(temps) >= 3 else temps[0]
        print(f"  Temperatura baseline    : {temp_baseline:.1f} °C")
        print(f"  Temperatura máxima      : {temp_max:.1f} °C  (Δ {temp_max - temp_baseline:+.1f} °C)")
        print(f"  Load baseline           : {load_baseline:.2f}")
        print(f"  Load máximo             : {load_max:.2f}")
        print(f"  Throttling Pi 4 a 80°C  : {'⚠ riesgo' if temp_max > 70 else '✓ sin riesgo'}")

    print()
    apto = True
    for topic in deltas:
        if abs(deltas[topic]["freq"]) > 10:
            print(f"  ⚠ {topic} degradación significativa de frecuencia ({deltas[topic]['freq']:+.1f}%)")
            apto = False
    if apto:
        print(f"  ✓ Sistema robusto: degradación < 10% en frecuencias bajo stress")

    lineas = [
        "% Tabla de tolerancia a saturación de CPU",
        "\\begin{tabular}{lrrr}",
        "\\toprule",
        "Métrica & Baseline & Durante estrés & Variación \\\\",
        "\\midrule",
    ]
    for topic in ["/scan", "/odom"]:
        if topic in deltas:
            b = base[topic]; s = stre[topic]
            lineas.append(f"Tasa \\texttt{{{topic}}} & "
                          f"\\SI{{{b['freq']:.2f}}}{{\\hertz}} & "
                          f"\\SI{{{s['freq']:.2f}}}{{\\hertz}} & "
                          f"${deltas[topic]['freq']:+.1f}\\,\\%$ \\\\")
            lineas.append(f"Jitter \\texttt{{{topic}}} & "
                          f"\\SI{{{b['p_std']:.2f}}}{{\\milli\\second}} & "
                          f"\\SI{{{s['p_std']:.2f}}}{{\\milli\\second}} & "
                          f"${deltas[topic]['jit']:+.1f}\\,\\%$ \\\\")
    if term:
        lineas.append(f"Temperatura SoC (peak) & "
                      f"\\SI{{{temp_baseline:.1f}}}{{\\celsius}} & "
                      f"\\SI{{{temp_max:.1f}}}{{\\celsius}} & "
                      f"$+{temp_max - temp_baseline:.1f}\\,°C$ \\\\")
        lineas.append(f"Load average (peak) & "
                      f"{load_baseline:.2f} & {load_max:.2f} & "
                      f"$+{(load_max/load_baseline - 1)*100:.0f}\\,\\%$ \\\\")
    lineas.append("\\bottomrule")
    lineas.append("\\end{tabular}")
    tex_path = os.path.join(SCRIPT_DIR, "tabla_stress_cpu.tex")
    with open(tex_path, "w") as f:
        f.write("\n".join(lineas))
    print(f"\n  LaTeX guardada en: {tex_path}")

    if term:
        fig, ax1 = plt.subplots(figsize=(10, 5))
        t_rel = [(r["ts"] - term[0]["ts"]).total_seconds() for r in term]
        loads = [r["load"] for r in term]
        temps = [r["temp"] for r in term]

        color1 = "tab:red"
        ax1.set_xlabel("Tiempo (s)")
        ax1.set_ylabel("Temperatura (°C)", color=color1)
        ax1.plot(t_rel, temps, color=color1, label="Temperatura SoC", linewidth=1.5)
        ax1.tick_params(axis="y", labelcolor=color1)
        ax1.axhline(80, color="red", linestyle=":", alpha=0.5, label="Throttling (80°C)")
        ax1.grid(alpha=0.3)

        ax2 = ax1.twinx()
        color2 = "tab:blue"
        ax2.set_ylabel("Load average (1 min)", color=color2)
        ax2.plot(t_rel, loads, color=color2, label="Load", linewidth=1.5)
        ax2.tick_params(axis="y", labelcolor=color2)
        ax2.axhline(4, color="blue", linestyle=":", alpha=0.5, label="Saturación (4 cores)")

        plt.title("Respuesta térmica y de carga durante saturación de CPU")
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc="best", fontsize=9)
        plt.tight_layout()
        for ext in ("pdf", "png"):
            path = os.path.join(SCRIPT_DIR, f"stress_cpu_temp.{ext}")
            plt.savefig(path, dpi=150)
        print(f"  Figura guardada: stress_cpu_temp.pdf / .png")
        plt.close()

    resumen = [
        f"Test de saturación de CPU",
        f"=" * 60,
        f"",
    ]
    for topic in ["/scan", "/odom"]:
        if topic in deltas:
            resumen.append(f"  {topic}:")
            resumen.append(f"    Baseline      : {base[topic]['freq']:.2f} Hz | jitter {base[topic]['p_std']:.2f} ms")
            resumen.append(f"    Durante stress: {stre[topic]['freq']:.2f} Hz | jitter {stre[topic]['p_std']:.2f} ms")
            resumen.append(f"    Δ frecuencia  : {deltas[topic]['freq']:+.1f}%")
            resumen.append(f"    Δ jitter      : {deltas[topic]['jit']:+.1f}%")
            resumen.append("")
    if term:
        resumen.append(f"  Pi (térmico/carga):")
        resumen.append(f"    Temperatura    : {temp_baseline:.1f}°C → peak {temp_max:.1f}°C")
        resumen.append(f"    Load average   : {load_baseline:.2f} → peak {load_max:.2f}")
        resumen.append(f"    Riesgo térmico : {'SI' if temp_max > 70 else 'NO'}")
        resumen.append("")
    resumen.append(f"  Veredicto: {'SISTEMA ROBUSTO' if apto else 'DEGRADACION SIGNIFICATIVA'}")

    with open(os.path.join(SCRIPT_DIR, "stress_cpu_resumen.txt"), "w") as f:
        f.write("\n".join(resumen))

if __name__ == "__main__":
    main()