#!/bin/bash

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

set +u
source /opt/ros/foxy/setup.bash 2>/dev/null || true
_WS_TMP="${HOME}/tesis_black_robot"
[ -f "${_WS_TMP}/install/setup.bash" ] && source "${_WS_TMP}/install/setup.bash"
export ROS_DOMAIN_ID=0
unset ROS_LOCALHOST_ONLY
if [ -f "${_WS_TMP}/src/articubot_one/config/cyclonedds_pc.xml" ]; then
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    export CYCLONEDDS_URI="file://${_WS_TMP}/src/articubot_one/config/cyclonedds_pc.xml"
fi
set -u

MODO="sim"
TIMEOUT_MIN="10"
OVERRIDE_OUTDIR=""
OVERRIDE_MAPDIR=""
NO_PROMPT=0
ITER_LABEL=""

POSITIONAL=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --outdir)       OVERRIDE_OUTDIR="$2"; shift 2 ;;
        --mapdir)       OVERRIDE_MAPDIR="$2"; shift 2 ;;
        --no-prompt)    NO_PROMPT=1; shift ;;
        --iter-label)   ITER_LABEL="$2"; shift 2 ;;
        *)              POSITIONAL+=("$1"); shift ;;
    esac
done
set -- "${POSITIONAL[@]}"

[ $# -ge 1 ] && MODO="$1"
[ $# -ge 2 ] && TIMEOUT_MIN="$2"

TIMEOUT_SEC=$(( TIMEOUT_MIN * 60 ))
TIMESTAMP="actual"
WS="${HOME}/tesis_black_robot"

# Sin versionamiento: nombres fijos por modo. Los archivos se sobrescriben.
SUFFIX_TS="${MODO}"

if [ -n "$OVERRIDE_OUTDIR" ]; then
    OUTDIR="$OVERRIDE_OUTDIR"
else
    OUTDIR="${WS}/experiments/exploracion/resultados_${MODO}"
fi

if [ -n "$OVERRIDE_MAPDIR" ]; then
    MAPDIR="$OVERRIDE_MAPDIR"
else
    MAPDIR="${WS}/src/articubot_one/maps/map_explore_${MODO}"
fi

mkdir -p "$OUTDIR" "$MAPDIR"

GUARDAR_MAPA_PY="${WS}/experiments/utils/guardar_mapa.py"

LOG_FILE="${OUTDIR}/explore_log_${MODO}.txt"
CSV_OUT="${OUTDIR}/explore_metricas_${MODO}.csv"
TEX_OUT="${OUTDIR}/explore_tabla_${MODO}.tex"
TEX_FALLOS="${OUTDIR}/explore_tabla_fallos_${MODO}.tex"
ODOM_CSV="${OUTDIR}/odom_trayectoria_${MODO}.csv"
MAPA_BASE="${MAPDIR}/mapa_explore_${MODO}"

USE_SIM_TIME="true"
[ "$MODO" = "real" ] && USE_SIM_TIME="false"

TMP_METAS="${OUTDIR}/.tmp_metas_${MODO}"
TMP_EXITOS="${OUTDIR}/.tmp_exitos_${MODO}"
TMP_FALLOS="${OUTDIR}/.tmp_fallos_${MODO}"
TMP_DONE="${OUTDIR}/.tmp_done_${MODO}"
TMP_INTERVENCIONES="${OUTDIR}/.tmp_interv_${MODO}"
echo 0 > "$TMP_METAS"
echo 0 > "$TMP_EXITOS"
echo 0 > "$TMP_FALLOS"
echo 0 > "$TMP_INTERVENCIONES"
rm -f "$TMP_DONE"

banner() {
    echo ""
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
}

verificar_sistema() {
    echo -e "${YELLOW}[PRE] Verificando SLAM + Nav2...${NC}"

    set +u
    [ -f "${WS}/install/setup.bash" ] && source "${WS}/install/setup.bash"
    if [ -f "${WS}/src/articubot_one/config/cyclonedds_pc.xml" ]; then
        export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
        export CYCLONEDDS_URI="file://${WS}/src/articubot_one/config/cyclonedds_pc.xml"
    fi
    export ROS_DOMAIN_ID=0
    unset ROS_LOCALHOST_ONLY
    set -u

    local MAP_OK=0
    local NAV2_OK=0

    echo -e "${YELLOW}  Esperando /map...${NC}"
    for i in {1..30}; do
        if ros2 topic list 2>/dev/null | grep -q '^/map$'; then
            MAP_OK=1
            break
        fi
        sleep 1
    done

    if [ "$MAP_OK" -ne 1 ]; then
        echo -e "${RED}ERROR: /map no disponible. Lanzar SLAM primero.${NC}"
        echo -e "${YELLOW}Tópicos visibles:${NC}"
        ros2 topic list 2>/dev/null || true
        exit 1
    fi

    echo -e "${YELLOW}  Esperando Nav2 activo...${NC}"
    for i in {1..45}; do
        if ros2 action list 2>/dev/null | grep -q '^/navigate_to_pose$'; then
            NAV2_OK=1
            break
        fi
        if ros2 service list 2>/dev/null | grep -q '/lifecycle_manager_navigation/is_active'; then
            NAV2_OK=1
            break
        fi
        sleep 1
    done

    if [ "$NAV2_OK" -ne 1 ]; then
        echo -e "${RED}ERROR: Nav2 no está activo o no es visible por DDS.${NC}"
        echo -e "${YELLOW}Servicios Nav2 visibles:${NC}"
        ros2 service list 2>/dev/null | grep -E 'lifecycle|controller|planner|costmap|navigate' || true
        echo -e "${YELLOW}Actions visibles:${NC}"
        ros2 action list 2>/dev/null || true
        echo -e "${YELLOW}Últimas líneas de /tmp/nav2_launch.log:${NC}"
        tail -80 /tmp/nav2_launch.log 2>/dev/null || true
        exit 1
    fi

    echo -e "${GREEN} ✓ SLAM y Nav2 activos${NC}"
}

lanzar_explore() {
    echo -e "${YELLOW}[1] Reiniciando explore_server para esta iteración...${NC}"
    if ros2 node list 2>/dev/null | grep -q '^/explore_server$'; then
        echo -e "${YELLOW} ⚠ explore_server ya existía. Se detendrá antes de relanzar.${NC}"
        killall -9 explore_server 2>/dev/null || true
        pkill -f 'explore.launch.py' 2>/dev/null || true
        sleep 2
    fi

    : > "$LOG_FILE"

    set +u
    [ -f "${WS}/install/setup.bash" ] && source "${WS}/install/setup.bash"
    if [ -f "${WS}/src/articubot_one/config/cyclonedds_pc.xml" ]; then
        export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
        export CYCLONEDDS_URI="file://${WS}/src/articubot_one/config/cyclonedds_pc.xml"
    fi
    export ROS_DOMAIN_ID=0
    unset ROS_LOCALHOST_ONLY
    set -u

    ros2 launch articubot_one explore.launch.py         use_sim_time:=${USE_SIM_TIME} >> "$LOG_FILE" 2>&1 &
    PID_EXPLORE=$!

    local OK=0
    for i in {1..20}; do
        if ros2 node list 2>/dev/null | grep -q '^/explore_server$'; then
            OK=1
            break
        fi
        sleep 1
    done

    if [ "$OK" -eq 1 ]; then
        echo -e "${GREEN} ✓ explore_server activo (PID=${PID_EXPLORE})${NC}"
        ros2 param dump /explore_server >> "$LOG_FILE" 2>/dev/null || true
    else
        echo -e "${RED} ✗ explore_server no arrancó. Revisar: ${LOG_FILE}${NC}"
        tail -80 "$LOG_FILE" 2>/dev/null || true
        exit 1
    fi
}

parsear_log_background() {
    tail -f "$LOG_FILE" 2>/dev/null | while IFS= read -r line; do
        if echo "$line" | grep -qi \
            'Sending goal\|Navigating to frontier\|Moving to frontier\|New goal'; then
            M=$(cat "$TMP_METAS")
            echo $(( M + 1 )) > "$TMP_METAS"
        fi
        if echo "$line" | grep -qi \
            'Goal succeeded\|Goal reached\|Reached frontier\|reached goal'; then
            E=$(cat "$TMP_EXITOS")
            echo $(( E + 1 )) > "$TMP_EXITOS"
        fi
        if echo "$line" | grep -qi \
            'Goal failed\|Goal aborted\|Aborting\|failed to reach'; then
            F=$(cat "$TMP_FALLOS")
            echo $(( F + 1 )) > "$TMP_FALLOS"
        fi
        if echo "$line" | grep -qi \
            'No frontiers\|no more frontiers\|exploration complete\|Finished exploring'; then
            touch "$TMP_DONE"
        fi
    done
}

grabar_log_explore() {
    {
        echo "===== DIAGNÓSTICO INICIAL EXPLORE/NAV2 ====="
        date
        echo "--- Nodes ---"
        ros2 node list 2>/dev/null | grep -E 'explore|controller|planner|bt_navigator|lifecycle' || true
        echo "--- Actions ---"
        ros2 action list 2>/dev/null || true
        echo "--- Topics cmd_vel ---"
        ros2 topic list 2>/dev/null | grep -E 'cmd_vel|navigate_to_pose|costmap|map|scan|odom' || true
        echo "--- Params explore_server ---"
        ros2 param dump /explore_server 2>/dev/null || true
        echo "===== FIN DIAGNÓSTICO INICIAL ====="
    } >> "$LOG_FILE" 2>&1

    ros2 topic echo /navigate_to_pose/_action/goal 2>/dev/null |         while IFS= read -r line; do
            TS=$(date '+%H:%M:%S')
            echo "[${TS}] ACTION_GOAL ${line}" >> "$LOG_FILE"
            if echo "$line" | grep -q 'goal_id:'; then
                M=$(cat "$TMP_METAS"); echo $(( M + 1 )) > "$TMP_METAS"
            fi
        done &
    PID_ACTION_GOALS=$!

    ros2 topic echo /navigate_to_pose/_action/status 2>/dev/null |         while IFS= read -r line; do
            TS=$(date '+%H:%M:%S')
            echo "[${TS}] ACTION_STATUS ${line}" >> "$LOG_FILE"
            if echo "$line" | grep -q 'status: 4'; then   # SUCCEEDED
                E=$(cat "$TMP_EXITOS"); echo $(( E + 1 )) > "$TMP_EXITOS"
            elif echo "$line" | grep -q 'status: 5\|status: 6'; then  # CANCELED/ABORTED
                F=$(cat "$TMP_FALLOS"); echo $(( F + 1 )) > "$TMP_FALLOS"
            fi
        done &
    PID_ACTION_STATUS=$!

    ros2 topic echo /cmd_vel 2>/dev/null |         while IFS= read -r line; do
            TS=$(date '+%H:%M:%S')
            echo "[${TS}] CMD_VEL ${line}" >> "$LOG_FILE"
        done &
    PID_CMDVEL_LOG=$!
}

watchdog_sin_metas() {
    sleep 45
    local M
    M=$(cat "$TMP_METAS" 2>/dev/null || echo 0)
    if [ "$M" -eq 0 ]; then
        {
            echo ""
            echo "===== WATCHDOG: 45 s sin metas de exploración ====="
            date
            echo "No se han detectado goals hacia /navigate_to_pose."
            echo "Esto suele indicar que explore_server no encontró fronteras válidas o quedó conectado a un costmap sin frontiers."
            echo "--- explore_server params ---"
            ros2 param dump /explore_server 2>/dev/null || true
            echo "--- costmap info ---"
            ros2 topic info /global_costmap/costmap 2>/dev/null || true
            ros2 topic echo /global_costmap/costmap --once 2>/dev/null | head -80 || true
            echo "--- action status ---"
            ros2 topic echo /navigate_to_pose/_action/status --once 2>/dev/null || true
            echo "===== FIN WATCHDOG ====="
        } >> "$LOG_FILE" 2>&1
        echo -e "
  ${YELLOW}⚠ 45 s sin metas de exploración. Revisa el log: ${LOG_FILE}${NC}"
    fi
}

TMP_DISTANCIA="${OUTDIR}/.tmp_dist_${MODO}"
echo "0.0" > "$TMP_DISTANCIA"

muestrear_odom_background() {
    echo "t_s,x,y,dist_acum_m" > "$ODOM_CSV"
    local T0
    T0=$(date +%s)
    local prev_x="" prev_y="" dist_acum=0.0

    while true; do
        local raw
        raw=$(ros2 topic echo /odom --once --field pose.pose.position 2>/dev/null || true)
        if [ -n "$raw" ]; then
            local x y
            x=$(echo "$raw" | grep -oP 'x: \K[-0-9.]+' | head -1 || true)
            y=$(echo "$raw" | grep -oP 'y: \K[-0-9.]+' | head -1 || true)
            if [ -n "$x" ] && [ -n "$y" ]; then
                local t_s=$(( $(date +%s) - T0 ))
                if [ -n "$prev_x" ] && [ -n "$prev_y" ]; then
                    dist_acum=$(awk "BEGIN {
                        dx = ${x} - ${prev_x}
                        dy = ${y} - ${prev_y}
                        printf \"%.3f\", ${dist_acum} + sqrt(dx*dx + dy*dy)
                    }")
                fi
                echo "${t_s},${x},${y},${dist_acum}" >> "$ODOM_CSV"
                echo "$dist_acum" > "$TMP_DISTANCIA"
                prev_x="$x"; prev_y="$y"
            fi
        fi
        sleep 2
    done
}

mostrar_progreso() {
    local T_INICIO=$1
    while true; do
        local ELAPSED=$(( $(date +%s) - T_INICIO ))
        local ELAPSED_MIN
        ELAPSED_MIN=$(awk "BEGIN {printf \"%.1f\", $ELAPSED/60}")
        local M E F DIST
        M=$(cat "$TMP_METAS")
        E=$(cat "$TMP_EXITOS")
        F=$(cat "$TMP_FALLOS")
        DIST=$(cat "$TMP_DISTANCIA" 2>/dev/null || echo "0.0")

        printf "\r  ${CYAN}⏱ %s min${NC}  |  metas: ${BOLD}%d${NC}  |  ✓ %d  |  ✗ %d  |  dist: %.1f m  |  [máx: %s min]" \
            "$ELAPSED_MIN" "$M" "$E" "$F" "$DIST" "$TIMEOUT_MIN"

        if [ -f "$TMP_DONE" ] || [ "$ELAPSED" -ge "$TIMEOUT_SEC" ]; then
            echo ""
            return 0
        fi
        sleep 3
    done
}

escuchar_intervenciones() {
    while true; do

        if read -r -t 1 -p "" tecla 2>/dev/null; then
            if [[ "$tecla" == "i" || "$tecla" == "I" ]]; then
                local N
                N=$(cat "$TMP_INTERVENCIONES")
                echo $(( N + 1 )) > "$TMP_INTERVENCIONES"
                echo -e "\n  ${YELLOW}[INTERVENCIÓN REGISTRADA: $(( N + 1 )) total]${NC}"
            fi
        fi

        [ -f "$TMP_DONE" ] && break
    done
}

guardar_mapa() {
    local NOMBRE="mapa_explore_${MODO}"

    python3 "$GUARDAR_MAPA_PY" \
        --destino    "$MAPDIR"   \
        --nombre     "$NOMBRE"   \
        --modo       "$MODO"     \
        --no-analizar            \
        --ws         "$WS"       \
    || echo -e "${RED} ✗ guardar_mapa.py terminó con error${NC}"
}

calcular_metricas_finales() {
    local DURACION_S=$1
    local PGM="${MAPA_BASE}.pgm"

    PGM="$PGM" \
    MODO_ENV="$MODO" \
    DURACION_S="$DURACION_S" \
    CSV_OUT="$CSV_OUT" \
    TEX_OUT="$TEX_OUT" \
    TEX_FALLOS="$TEX_FALLOS" \
    ODOM_CSV="$ODOM_CSV" \
    TMP_METAS="$TMP_METAS" \
    TMP_EXITOS="$TMP_EXITOS" \
    TMP_FALLOS="$TMP_FALLOS" \
    TMP_INTERVENCIONES="$TMP_INTERVENCIONES" \
    SUFFIX_TS="$SUFFIX_TS" \
    python3 - <<'PYEOF'
import os, csv
from datetime import datetime

pgm_path       = os.environ["PGM"]
modo           = os.environ["MODO_ENV"]
duracion_s     = float(os.environ["DURACION_S"])
csv_out        = os.environ["CSV_OUT"]
tex_out        = os.environ["TEX_OUT"]
tex_fallos     = os.environ["TEX_FALLOS"]
odom_csv       = os.environ["ODOM_CSV"]
ts             = os.environ["SUFFIX_TS"]
metas          = int(open(os.environ["TMP_METAS"]).read().strip() or 0)
exitos         = int(open(os.environ["TMP_EXITOS"]).read().strip() or 0)
fallos         = int(open(os.environ["TMP_FALLOS"]).read().strip() or 0)
intervenciones = int(open(os.environ["TMP_INTERVENCIONES"]).read().strip() or 0)
cobertura = None
area_libre = None
if os.path.exists(pgm_path):
    try:
        with open(pgm_path, 'rb') as f:
            header = []
            while len(header) < 4:
                line = f.readline().decode('ascii', errors='ignore').strip()
                if line.startswith('#'):
                    continue
                header.extend(line.split())
            magic = header[0]
            w, h = int(header[1]), int(header[2])
            if magic == 'P5':
                import numpy as np
                data       = np.frombuffer(f.read(), dtype='uint8').reshape((h, w))
                libre      = int((data >= 230).sum())
                desc       = int(((data > 50) & (data < 230)).sum())
                total      = libre + desc
                cobertura  = round(libre / total * 100, 1) if total > 0 else 0.0
                area_libre = round(libre * 0.05**2, 2)
    except Exception as e:
        print(f"  AVISO cobertura: {e}")
dist_total = None
if os.path.exists(odom_csv):
    try:
        with open(odom_csv) as f:
            rows = list(csv.DictReader(f))
        if rows:
            dist_total = float(rows[-1]['dist_acum_m'])
    except Exception as e:
        print(f"  AVISO distancia: {e}")

dur_min    = round(duracion_s / 60, 1)
cob_str    = f'{cobertura:.1f}'  if cobertura  is not None else '---'
area_str   = f'{area_libre:.2f}' if area_libre is not None else '---'
dist_str   = f'{dist_total:.1f}' if dist_total is not None else '---'
tasa_str   = f'{exitos/max(1,metas)*100:.0f}' if metas > 0 else '---'
interv_str = str(intervenciones)
rows_csv = [
    ['indicador', 'valor', 'unidad'],
    ['modo',             modo,       ''],
    ['timestamp',        ts,         ''],
    ['duracion',         dur_min,    'min'],
    ['metas_generadas',  metas,      ''],
    ['metas_alcanzadas', exitos,     ''],
    ['metas_fallidas',   fallos,     ''],
    ['tasa_exito',       tasa_str,   '%'],
    ['cobertura',        cob_str,    '%'],
    ['area_libre',       area_str,   'm2'],
    ['distancia_total',  dist_str,   'm'],
    ['intervenciones',   interv_str, ''],
]
with open(csv_out, 'w', newline='') as f:
    csv.writer(f).writerows(rows_csv)
print(f"  ✓ CSV: {csv_out}")
caption = ('Indicadores de exploración autónoma en simulación.'
           if modo == 'sim' else
           'Indicadores de exploración autónoma en hardware real.')

lines = [
    f'% Generado por run_explore.sh — {datetime.now().strftime("%Y-%m-%d %H:%M")}',
    r'\begin{table}[H]', r'\centering',
    f'\\caption{{{caption}}}',
    f'\\label{{tab:explore_{modo}}}',
    r'\begin{tabular}{ll}', r'\hline',
    r'\textbf{Indicador} & \textbf{Valor} \\', r'\hline',
    f'Tiempo hasta finalización          & {dur_min}~min \\\\',
    f'Número de metas generadas          & {metas} \\\\',
    f'Metas alcanzadas exitosamente      & {exitos} \\\\',
    f'Metas fallidas o abortadas         & {fallos} \\\\',
    f'Tasa de éxito de metas             & {tasa_str}~\\% \\\\',
    f'Cobertura estimada del entorno     & {cob_str}~\\% \\\\',
    f'Distancia total recorrida          & {dist_str}~m \\\\',
    f'Intervenciones manuales requeridas & {interv_str} \\\\',
    r'\hline', r'\end{tabular}', r'\end{table}',
    '',
    f'% Area libre mapeada (extra): {area_str} m^2',
]
with open(tex_out, 'w') as f:
    f.write('\n'.join(lines))
print(f"  ✓ LaTeX principal: {tex_out}")
if os.path.exists(odom_csv):
    try:
        with open(odom_csv) as f:
            traj_rows = list(csv.DictReader(f))
        if traj_rows:
            t_vals = [float(r['t_s']) for r in traj_rows]
            d_vals = [float(r['dist_acum_m']) for r in traj_rows]
            v_vals = []
            for i in range(1, len(d_vals)):
                dt = t_vals[i] - t_vals[i-1]
                if dt > 0:
                    v_vals.append((d_vals[i] - d_vals[i-1]) / dt)
            v_media = sum(v_vals)/len(v_vals) if v_vals else 0.0
            v_max   = max(v_vals)             if v_vals else 0.0
            n_muestras = len(traj_rows)
            tex_traj = tex_out.replace('_tabla_', '_trayectoria_')
            traj_lines = [
                f'% Estadísticas de trayectoria — {datetime.now().strftime("%Y-%m-%d %H:%M")}',
                r'\begin{table}[H]', r'\centering',
                f'\\caption{{Estadísticas de trayectoria durante exploración en {modo}.}}',
                f'\\label{{tab:trayectoria_explore_{modo}}}',
                r'\begin{tabular}{ll}', r'\hline',
                r'\textbf{Parámetro} & \textbf{Valor} \\', r'\hline',
                f'Muestras de \\texttt{{/odom}} registradas & {n_muestras} \\\\',
                f'Distancia total recorrida                 & {dist_str}~m \\\\',
                f'Velocidad media estimada                  & {v_media:.3f}~m/s \\\\',
                f'Velocidad pico estimada                   & {v_max:.3f}~m/s \\\\',
                f'Duración total                            & {dur_min}~min \\\\',
                r'\hline', r'\end{tabular}', r'\end{table}',
            ]
            with open(tex_traj, 'w') as f:
                f.write('\n'.join(traj_lines))
            print(f"  ✓ LaTeX trayectoria: {tex_traj}")
    except Exception as e:
        print(f"  AVISO trayectoria tex: {e}")
PYEOF
}

limpiar() {
    rm -f "$TMP_METAS" "$TMP_EXITOS" "$TMP_FALLOS" "$TMP_DONE" \
          "$TMP_INTERVENCIONES" "$TMP_DISTANCIA" 2>/dev/null || true
    [ -n "$PID_LOG_PARSER" ] && kill "$PID_LOG_PARSER" 2>/dev/null || true
    [ -n "$PID_LOG_GRAB"   ] && kill "$PID_LOG_GRAB"   2>/dev/null || true
    [ -n "$PID_ACTION_GOALS" ] && kill "$PID_ACTION_GOALS" 2>/dev/null || true
    [ -n "$PID_ACTION_STATUS" ] && kill "$PID_ACTION_STATUS" 2>/dev/null || true
    [ -n "$PID_CMDVEL_LOG" ] && kill "$PID_CMDVEL_LOG" 2>/dev/null || true
    [ -n "$PID_WATCHDOG"   ] && kill "$PID_WATCHDOG"   2>/dev/null || true
    [ -n "$PID_ODOM"       ] && kill "$PID_ODOM"       2>/dev/null || true
    [ -n "$PID_INTERV"     ] && kill "$PID_INTERV"     2>/dev/null || true
    [ -n "$PID_EXPLORE"    ] && kill "$PID_EXPLORE"    2>/dev/null || true
}

PID_LOG_PARSER=""
PID_LOG_GRAB=""
PID_ODOM=""
PID_INTERV=""
PID_EXPLORE=""
PID_ACTION_GOALS=""
PID_ACTION_STATUS=""
PID_CMDVEL_LOG=""
PID_WATCHDOG=""

trap limpiar EXIT

banner "EXPLORACIÓN AUTÓNOMA DE FRONTERAS — modo: ${MODO^^}"
[ -n "$ITER_LABEL" ] && echo -e "  ${BOLD}Iteración: ${ITER_LABEL}${NC}"
echo -e "  Timeout máximo: ${TIMEOUT_MIN} min"
echo -e "  Mapa se guardará en: ${MAPDIR}/"
echo -e "  Log en: ${LOG_FILE}"
echo -e "  ${CYAN}Presiona 'i' + ENTER en cualquier momento para registrar una intervención manual.${NC}\n"

verificar_sistema

if [ "$MODO" = "real" ]; then
    echo -e "${YELLOW}  PRECAUCIÓN: Ten el mando siempre en la mano.${NC}"
    echo -e "${YELLOW}  Presiona dead-man switch si el robot se dirige a un obstáculo.${NC}"
    echo -e "${YELLOW}  Pulsa 'i'+ENTER cada vez que uses el mando para registrar la intervención.${NC}\n"
fi

if [ "$NO_PROMPT" -eq 0 ]; then
    echo -n "  ¿Continuar? [ENTER / Ctrl+C para cancelar]: "
    read -r
else
    echo -e "${CYAN}  Modo no-interactivo (--no-prompt) — iniciando exploración...${NC}"
fi
: > "$LOG_FILE"
parsear_log_background &
PID_LOG_PARSER=$!
sleep 0.5

lanzar_explore
grabar_log_explore &
PID_LOG_GRAB=$!
watchdog_sin_metas &
PID_WATCHDOG=$!
muestrear_odom_background &
PID_ODOM=$!

if [ "$NO_PROMPT" -eq 0 ]; then
    escuchar_intervenciones &
    PID_INTERV=$!
fi

T_INICIO=$(date +%s)
echo ""
echo -e "  ${GREEN}Exploración en progreso...${NC}"
echo -e "  ${CYAN}Ctrl+C para detener manualmente y guardar mapa.${NC}"
if [ "$NO_PROMPT" -eq 0 ]; then
    echo -e "  ${CYAN}Pulsa 'i'+ENTER para registrar intervención manual.${NC}\n"
fi

mostrar_progreso "$T_INICIO"

T_FIN=$(date +%s)
DURACION=$(( T_FIN - T_INICIO ))

if [ -f "$TMP_DONE" ]; then
    echo -e "${GREEN}  ✓ Exploración completada (no quedan fronteras)${NC}"
elif [ "$DURACION" -ge "$TIMEOUT_SEC" ]; then
    echo -e "${YELLOW}  ⏱ Timeout alcanzado (${TIMEOUT_MIN} min)${NC}"
fi

guardar_mapa
sleep 2

echo ""
echo -e "${CYAN}  Calculando métricas...${NC}"
calcular_metricas_finales "$DURACION"

M=$(cat "$TMP_METAS");   E=$(cat "$TMP_EXITOS");   F=$(cat "$TMP_FALLOS")
I=$(cat "$TMP_INTERVENCIONES")
DIST=$(cat "$TMP_DISTANCIA" 2>/dev/null || echo "0.0")
DUR_MIN=$(awk "BEGIN {printf \"%.1f\", $DURACION/60}")

banner "RESUMEN EXPLORACIÓN"
[ -n "$ITER_LABEL" ] && echo -e "  ${BOLD}Iteración: ${ITER_LABEL}${NC}"
echo -e "  Duración total:              ${DUR_MIN} min"
echo -e "  Metas generadas:             ${M}"
echo -e "  Metas alcanzadas:            ${E}"
echo -e "  Metas fallidas:              ${F}"
echo -e "  Intervenciones manuales:     ${I}"
echo -e "  Distancia estimada:          ${DIST} m"
echo -e "  Mapa:                        ${MAPDIR}/"
echo -e ""
if [ "$I" -eq 0 ]; then
    echo -e "  ${GREEN}✓ Sin intervenciones manuales — operación completamente autónoma.${NC}"
else
    echo -e "  ${YELLOW}⚠ ${I} intervención(es) manual(es) registrada(s).${NC}"
fi
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"