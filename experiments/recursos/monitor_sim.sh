#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="${HOME}/tesis_black_robot/test/recursos"
DURACION="${1:-60}"          # segundos de medición (default 60s)
ETIQUETA="${2:-sim}"         # nombre lógico del resultado, sin timestamp
INTERVALO=2                  # segundos entre muestras
TIMESTAMP="actual"

RESULT_DIR="${SCRIPT_DIR}/monitor_sim/${ETIQUETA}"
mkdir -p "$RESULT_DIR"
CSV_OUT="${RESULT_DIR}/monitor_sim.csv"
PNG_OUT="${RESULT_DIR}/monitor_sim.png"
TEX_OUT="${RESULT_DIR}/monitor_sim.tex"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN} Monitor de Recursos — Simulación (PC)${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e " Duración  : ${DURACION} s"
echo -e " Intervalo : ${INTERVALO} s"
echo -e " Muestras  : $(( DURACION / INTERVALO ))"
echo -e " CSV       : ${CSV_OUT}"
echo ""
if ! timeout 5 ros2 topic list 2>/dev/null | grep -q "/clock"; then
    echo -e "${RED}ERROR: /clock no disponible. Lanza launch_sim_all.sh primero.${NC}"
    exit 1
fi
echo -e "${GREEN} ✓ Simulación activa${NC}"
echo ""
check_cmd() {
    command -v "$1" &>/dev/null || {
        echo -e "${YELLOW}AVISO: '$1' no instalado. Instalar con: sudo apt install $2${NC}"
        return 1
    }
}
HAS_MPSTAT=true; check_cmd mpstat sysstat || HAS_MPSTAT=false
HAS_FREE=true;   check_cmd free procps    || HAS_FREE=false
get_process_metrics() {
    local gz_cpu gz_mem slam_cpu slam_mem nav_cpu nav_mem total_cpu total_mem
    gz_cpu=$(ps aux | awk '/gzserver/{sum+=$3} END{printf "%.1f", sum+0}')
    gz_mem=$(ps aux | awk '/gzserver/{sum+=$4} END{printf "%.1f", sum+0}')
    slam_cpu=$(ps aux | awk '/async_slam/{sum+=$3} END{printf "%.1f", sum+0}')
    slam_mem=$(ps aux | awk '/async_slam/{sum+=$4} END{printf "%.1f", sum+0}')
    nav_cpu=$(ps aux | awk '/controller_server|planner_server|bt_navigator/{sum+=$3} END{printf "%.1f", sum+0}')
    nav_mem=$(ps aux | awk '/controller_server|planner_server|bt_navigator/{sum+=$4} END{printf "%.1f", sum+0}')
    echo "${gz_cpu},${gz_mem},${slam_cpu},${slam_mem},${nav_cpu},${nav_mem}"
}
echo "timestamp_s,cpu_total_pct,ram_used_mb,ram_total_mb,ram_pct,"\
"cpu_gzserver_pct,ram_gzserver_pct,"\
"cpu_slam_pct,ram_slam_pct,"\
"cpu_nav2_pct,ram_nav2_pct" > "${CSV_OUT}"
RAM_TOTAL_MB=$(free -m | awk '/^Mem:/{print $2}')
T_START=$(date +%s)
T_END=$(( T_START + DURACION ))
N_MUESTRAS=0

echo -e "${YELLOW}Midiendo... (Ctrl+C para detener antes)${NC}"
echo -e " ${CYAN}t(s)   CPU%  RAM_MB  gzserver  SLAM    Nav2${NC}"

while [ "$(date +%s)" -lt "${T_END}" ]; do
    T_NOW=$(( $(date +%s) - T_START ))
    if [ "$HAS_MPSTAT" = true ]; then
        CPU_TOTAL=$(mpstat 1 1 | awk '/Average:.*all/{printf "%.1f", 100-$NF}')
    else
        CPU_TOTAL=$(top -bn2 | awk '/^%Cpu/{last=$2} END{printf "%.1f", last}')
    fi
    RAM_USED_MB=$(free -m | awk '/^Mem:/{print $3}')
    RAM_PCT=$(awk "BEGIN {printf \"%.1f\", ${RAM_USED_MB}/${RAM_TOTAL_MB}*100}")
    PROCS=$(get_process_metrics)
    IFS=',' read -r gz_cpu gz_mem slam_cpu slam_mem nav_cpu nav_mem <<< "$PROCS"
    echo "${T_NOW},${CPU_TOTAL},${RAM_USED_MB},${RAM_TOTAL_MB},${RAM_PCT},"\
"${gz_cpu},${gz_mem},${slam_cpu},${slam_mem},${nav_cpu},${nav_mem}" \
        >> "${CSV_OUT}"
    printf " %4ds  %5s%%  %6s MB   %5s%%   %5s%%  %5s%%\n" \
        "${T_NOW}" "${CPU_TOTAL}" "${RAM_USED_MB}" \
        "${gz_cpu}" "${slam_cpu}" "${nav_cpu}"

    N_MUESTRAS=$(( N_MUESTRAS + 1 ))
    sleep "${INTERVALO}"
done

echo ""
echo -e "${GREEN} ✓ Medición completada (${N_MUESTRAS} muestras)${NC}"
python3 - <<PYEOF
import csv, os
import numpy as np

csv_path = "${CSV_OUT}"
png_path = "${PNG_OUT}"
tex_path = "${TEX_OUT}"

rows = []
with open(csv_path) as f:
    for row in csv.DictReader(f):
        rows.append({k: float(v) for k, v in row.items()})

if not rows:
    print("  Sin datos para analizar.")
    exit(0)

t         = np.array([r["timestamp_s"]    for r in rows])
cpu_total = np.array([r["cpu_total_pct"]  for r in rows])
ram_mb    = np.array([r["ram_used_mb"]    for r in rows])
ram_pct   = np.array([r["ram_pct"]        for r in rows])
cpu_gz    = np.array([r["cpu_gzserver_pct"]  for r in rows])
cpu_slam  = np.array([r["cpu_slam_pct"]   for r in rows])
cpu_nav   = np.array([r["cpu_nav2_pct"]   for r in rows])
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True)
ax = axes[0]
ax.plot(t, cpu_total, "k-",   lw=1.5, label="CPU total sistema", zorder=5)
ax.fill_between(t, 0, cpu_gz,    alpha=0.4, label="gzserver",  color="#E07070")
ax.fill_between(t, 0, cpu_slam,  alpha=0.4, label="SLAM",      color="#70A0E0")
ax.fill_between(t, 0, cpu_nav,   alpha=0.4, label="Nav2",      color="#70C070")
ax.set_ylabel("CPU (%)")
ax.set_title("Uso de CPU — simulación (PC)")
ax.legend(loc="upper right", fontsize=8)
ax.set_ylim(0, 110)
ax.grid(linestyle="--", alpha=0.5)
ax.axhline(80, color="red", linestyle=":", lw=1, label="80%")
ax2 = axes[1]
ax2.plot(t, ram_mb,  "#4C72B0", lw=1.5, label=f"RAM usada (total: {int(ram_mb.max()+0.5)} MB)")
ax2.fill_between(t, 0, ram_mb, alpha=0.3, color="#4C72B0")
ax2.set_xlabel("Tiempo (s)")
ax2.set_ylabel("RAM (MB)")
ax2.set_title("Uso de RAM — simulación (PC)")
ax2.legend(loc="upper right", fontsize=8)
ax2.grid(linestyle="--", alpha=0.5)

plt.tight_layout()
plt.savefig(png_path, dpi=150, bbox_inches="tight")
plt.close()
print(f"  ✓ PNG: {png_path}")
from datetime import datetime
now = datetime.now().strftime("%Y-%m-%d %H:%M")
ram_total_mb = rows[0]["ram_total_mb"]

lines = [
    f"% Generado por monitor_sim.sh — {now}",
    r"\begin{table}[H]",
    r"\centering",
    r"\caption{Uso de recursos computacionales del PC durante la simulaci\'on.}",
    r"\label{tab:recursos_sim}",
    r"\begin{tabular}{lcccc}",
    r"\hline",
    r"\textbf{M\'etrica} & \textbf{M\'in} & \textbf{Media} & \textbf{M\'ax} & \textbf{Unidad} \\",
    r"\hline",
    f"CPU total sistema & {cpu_total.min():.1f} & {cpu_total.mean():.1f} & {cpu_total.max():.1f} & \\% \\\\",
    f"CPU gzserver & {cpu_gz.min():.1f} & {cpu_gz.mean():.1f} & {cpu_gz.max():.1f} & \\% \\\\",
    f"CPU SLAM Toolbox & {cpu_slam.min():.1f} & {cpu_slam.mean():.1f} & {cpu_slam.max():.1f} & \\% \\\\",
    f"CPU Nav2 & {cpu_nav.min():.1f} & {cpu_nav.mean():.1f} & {cpu_nav.max():.1f} & \\% \\\\",
    r"\hline",
    f"RAM usada & {ram_mb.min():.0f} & {ram_mb.mean():.0f} & {ram_mb.max():.0f} & MB \\\\",
    f"RAM \\% sistema & {ram_pct.min():.1f} & {ram_pct.mean():.1f} & {ram_pct.max():.1f} & \\% \\\\",
    r"\hline",
    f"RAM total PC & \\multicolumn{{4}}{{l}}{{{int(ram_total_mb):.0f} MB}} \\\\",
    f"Duración medición & \\multicolumn{{4}}{{l}}{{{int(t.max())} s ({len(rows)} muestras)}} \\\\",
    r"\hline",
    r"\end{tabular}",
    r"\end{table}",
]
with open(tex_path, "w") as f:
    f.write("\n".join(lines))
print(f"  ✓ LaTeX: {tex_path}")
print(f"\n  Resumen:")
print(f"    CPU media total : {cpu_total.mean():.1f}%  (max: {cpu_total.max():.1f}%)")
print(f"    RAM media       : {ram_mb.mean():.0f} MB  (max: {ram_mb.max():.0f} MB)")
print(f"    CPU gzserver    : {cpu_gz.mean():.1f}%  (max: {cpu_gz.max():.1f}%)")
print(f"    CPU SLAM        : {cpu_slam.mean():.1f}%  (max: {cpu_slam.max():.1f}%)")
print(f"    CPU Nav2        : {cpu_nav.mean():.1f}%  (max: {cpu_nav.max():.1f}%)")
PYEOF

echo ""
echo -e "${GREEN}=== LISTO ===${NC}"
echo -e "Archivos generados:"
echo -e "  ${CSV_OUT}"
echo -e "  ${PNG_OUT}  ← figura para tesis (tab:recursos_sim)"
echo -e "  ${TEX_OUT}  ← tabla LaTeX"
echo ""