#!/bin/bash

INTERVALO="${1:-5}"
DURACION_MIN="${2:-10}"
ETIQUETA="${3:-prueba}"
TIMESTAMP="actual"
DURACION_S=$(( DURACION_MIN * 60 ))
OUTDIR="${HOME}/robot_ws/test/recursos"
RESULT_DIR="${OUTDIR}/monitor_pi/${ETIQUETA}"
mkdir -p "$RESULT_DIR"
CSV_OUT="${RESULT_DIR}/monitor_pi.csv"
TEX_OUT="${RESULT_DIR}/monitor_pi_resumen.tex"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo "timestamp_s,cpu_pct,ram_used_mb,ram_total_mb,temp_c,scan_latency_ms,throttle_flag" \
    > "$CSV_OUT"

leer_cpu() {
    local line1 line2
    line1=$(grep -m1 '^cpu ' /proc/stat)
    sleep 0.5
    line2=$(grep -m1 '^cpu ' /proc/stat)

    local idle1 total1 idle2 total2
    idle1=$(echo $line1 | awk '{print $5}')
    total1=$(echo $line1 | awk '{s=0; for(i=2;i<=NF;i++) s+=$i; print s}')
    idle2=$(echo $line2 | awk '{print $5}')
    total2=$(echo $line2 | awk '{s=0; for(i=2;i<=NF;i++) s+=$i; print s}')

    awk "BEGIN {
        d_idle  = ${idle2}  - ${idle1}
        d_total = ${total2} - ${total1}
        if (d_total > 0)
            printf \"%.1f\", (1 - d_idle/d_total)*100
        else
            print \"0.0\"
    }"
}

leer_ram() {
    local total used available
    total=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    available=$(grep MemAvailable /proc/meminfo | awk '{print $2}')
    used=$(( total - available ))
    echo "$(( used / 1024 )) $(( total / 1024 ))"
}

leer_temp() {
    if command -v vcgencmd &>/dev/null; then
        vcgencmd measure_temp 2>/dev/null | sed "s/temp=//;s/'C//"
    elif [ -f /sys/class/thermal/thermal_zone0/temp ]; then
        awk '{printf "%.1f", $1/1000}' /sys/class/thermal/thermal_zone0/temp
    else
        echo "---"
    fi
}

leer_throttle() {
    if command -v vcgencmd &>/dev/null; then
        local th
        th=$(vcgencmd get_throttled 2>/dev/null | sed 's/throttled=//')
        [ "$th" = "0x0" ] && echo "0" || echo "1"
    else
        echo "0"
    fi
}

leer_scan_latency() {
    if ! command -v ros2 &>/dev/null; then
        echo "---"
        return
    fi
    local out
    out=$(timeout 3 ros2 topic delay /scan 2>/dev/null | \
          grep -i 'average\|mean\|delay' | \
          grep -oP '[0-9]+\.[0-9]+' | head -1)
    if [ -n "$out" ]; then
        awk "BEGIN {printf \"%.1f\", ${out}*1000}"
    else
        echo "---"
    fi
}

T_INICIO=$(date +%s)
MUESTRA=0

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "${CYAN}  Monitor Pi — ${ETIQUETA} | cada ${INTERVALO}s | ${DURACION_MIN} min${NC}"
echo -e "${CYAN}  Salida: ${CSV_OUT}${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════${NC}"
echo -e "  ${YELLOW}Ctrl+C para detener y generar resumen.${NC}\n"
printf "  %-10s %-8s %-12s %-8s %-14s\n" "t(s)" "CPU%" "RAM(MB)" "Temp(°C)" "Scan lat(ms)"
printf "  %-10s %-8s %-12s %-8s %-14s\n" "──────────" "──────" "──────────" "──────" "─────────────"

generar_resumen() {
    python3 - <<PYEOF
import csv, os
from datetime import datetime

csv_path  = "${CSV_OUT}"
tex_path  = "${TEX_OUT}"
etiqueta  = "${ETIQUETA}"

rows = []
with open(csv_path) as f:
    for row in csv.DictReader(f):
        rows.append(row)

if not rows:
    print("  Sin datos.")
    exit()

def vals(key):
    return [float(r[key]) for r in rows if r.get(key, '---') not in ('---', '', 'N/A')]

cpu   = vals('cpu_pct')
ram   = vals('ram_used_mb')
temp  = vals('temp_c')
scan  = vals('scan_latency_ms')

def fmt_stat(v):
    if not v: return '---', '---'
    return f'{sum(v)/len(v):.1f}', f'{max(v):.1f}'

cpu_m,  cpu_p  = fmt_stat(cpu)
ram_m,  ram_p  = fmt_stat(ram)
temp_m, temp_p = fmt_stat(temp)
scan_m, scan_p = fmt_stat(scan)
ram_tot = rows[0].get('ram_total_mb', '8192') if rows else '8192'
try:
    ram_tot_gb = f'{float(ram_tot)/1024:.1f}'
except:
    ram_tot_gb = '---'

throttle_events = sum(1 for r in rows if r.get('throttle_flag','0') == '1')
dur_min = len(rows) * ${INTERVALO} / 60

lines = [
    f'% Generado por monitor_pi.sh — {datetime.now().strftime("%Y-%m-%d %H:%M")}',
    f'% Prueba: {etiqueta} | {len(rows)} muestras cada ${INTERVALO}s',
    r'\begin{table}[H]', r'\centering',
    r'\caption{Uso de recursos de la Raspberry~Pi~4 durante operación combinada SLAM + Nav2.}',
    r'\label{tab:recursos_pi}',
    r'\begin{tabular}{lcc}', r'\hline',
    r'\textbf{Recurso} & \textbf{Valor típico} & \textbf{Pico observado} \\',
    r'\hline',
    f'CPU (4 núcleos, \\%) & {cpu_m}~\\% & {cpu_p}~\\% \\\\',
    (f'RAM utilizada (de {ram_tot_gb}~GB) & {float(ram_m)/1024:.2f}~GB & {float(ram_p)/1024:.2f}~GB \\\\'
        if ram_m not in ("---", "") else f'RAM utilizada (de {ram_tot_gb}~GB) & ---~GB & ---~GB \\\\'),
    f'Temperatura del SoC & {temp_m}~°C & {temp_p}~°C \\\\',
    f'Latencia \\texttt{{/scan}} & {scan_m}~ms & {scan_p}~ms \\\\',
    f'% Eventos de throttling observados: {throttle_events}',
    r'\hline', r'\end{tabular}', r'\end{table}',
]
with open(tex_path, 'w') as f:
    f.write('\n'.join(lines))
print(f'  ✓ {tex_path}')
print(f'  Resumen: CPU {cpu_m}% (max {cpu_p}%) | RAM {ram_m} MB | Temp {temp_m}°C (max {temp_p}°C) | /scan {scan_m} ms')
PYEOF
}

trap 'echo ""; echo -e "${YELLOW}Generando resumen...${NC}"; generar_resumen; exit 0' SIGINT SIGTERM

while true; do
    ELAPSED=$(( $(date +%s) - T_INICIO ))
    [ "$ELAPSED" -ge "$DURACION_S" ] && break

    MUESTRA=$(( MUESTRA + 1 ))
    CPU=$(leer_cpu)
    read -r RAM_USED RAM_TOTAL <<< "$(leer_ram)"
    TEMP=$(leer_temp)
    THROTTLE=$(leer_throttle)

    if (( MUESTRA % 10 == 1 )); then
        SCAN_LAT=$(leer_scan_latency)
    fi
    SCAN_LAT="${SCAN_LAT:----}"

    echo "${ELAPSED},${CPU},${RAM_USED},${RAM_TOTAL},${TEMP},${SCAN_LAT},${THROTTLE}" \
        >> "$CSV_OUT"

    TEMP_COLOR="$GREEN"
    TEMP_NUM="${TEMP//---/0}"
    (( $(echo "$TEMP_NUM > 75" | bc -l 2>/dev/null || echo 0) )) && TEMP_COLOR="$RED"
    (( $(echo "$TEMP_NUM > 65" | bc -l 2>/dev/null || echo 0) )) && TEMP_COLOR="$YELLOW"

    printf "  %-10s %-8s %-12s ${TEMP_COLOR}%-8s${NC} %-14s\n" \
        "${ELAPSED}s" "${CPU}%" "${RAM_USED}/${RAM_TOTAL}" "${TEMP}°C" "${SCAN_LAT}ms"

    if command -v bc &>/dev/null && (( $(echo "${TEMP//---/0} > 80" | bc -l) )); then
        echo -e "  ${RED}⚠ TEMPERATURA ALTA: ${TEMP}°C — posible throttling${NC}"
    fi

    sleep "$INTERVALO"
done

echo ""
echo -e "${YELLOW}Duración alcanzada (${DURACION_MIN} min). Generando resumen...${NC}"
generar_resumen

echo ""
echo -e "${GREEN}Monitoreo finalizado.${NC}"
echo -e "  CSV:    ${CSV_OUT}"
echo -e "  LaTeX:  ${TEX_OUT}"