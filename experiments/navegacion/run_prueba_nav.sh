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
set -u

MODO="${1:-sim}"
TIMESTAMP="actual"
WS="${HOME}/tesis_black_robot"

# Sin versionamiento: carpeta fija por modo; se sobrescribe en cada ejecución.
OUTDIR="${WS}/experiments/navegacion/nav_${MODO}"
mkdir -p "$OUTDIR"

CSV_OUT="${OUTDIR}/nav_resultados_${MODO}.csv"
TEX_OUT="${OUTDIR}/nav_tabla_${MODO}.tex"
TEX_FALLOS="${OUTDIR}/nav_tabla_fallos_${MODO}.tex"
LOG_OUT="${OUTDIR}/nav_log_${MODO}.txt"

TIMEOUT_META=120      # segundos máximos por meta antes de declarar fallo
REPS=5
TOLERANCIA_SIM=0.25   # m — xy_goal_tolerance en nav2_params_sim.yaml
TOLERANCIA_REAL=0.22  # m — xy_goal_tolerance en nav2_params.yaml

TOLERANCIA="$TOLERANCIA_SIM"
[ "$MODO" = "real" ] && TOLERANCIA="$TOLERANCIA_REAL"

declare -A POSES_SIM
POSES_SIM[1]="2.2 -2.5 0.0 1.0"      # Escenario 1: meta directa, camino libre
POSES_SIM[2]="2.2  0.5 0.0 1.0"      # Escenario 2: box_01(0,0) intercepta ruta
POSES_SIM[3]="2.2  3.0 0.0 0.707"    # Escenario 3: pasillo junto a box_04

declare -A NOMBRES
NOMBRES[1]="Meta directa sin obstáculos"
NOMBRES[2]="Meta con obstáculo intermedio"
NOMBRES[3]="Pasillo o zona estrecha"

TIPO_FALLO_OPCIONES=(
    "1) Costmap bloqueado (obstáculo no mapeado)"
    "2) Ruta inválida (espacio muy estrecho)"
    "3) Robot atascado (deslizamiento en giro)"
    "4) Timeout de navegación (oscilación local)"
    "5) Otro (describir en observación)"
)

declare -A TIPO_FALLO_KEY
TIPO_FALLO_KEY[1]="costmap_bloqueado"
TIPO_FALLO_KEY[2]="ruta_invalida"
TIPO_FALLO_KEY[3]="robot_atascado"
TIPO_FALLO_KEY[4]="timeout_oscilacion"
TIPO_FALLO_KEY[5]="otro"

declare -A TIPO_FALLO_RECUPERACION
TIPO_FALLO_RECUPERACION[1]="ClearCostmapAroundRobot"
TIPO_FALLO_RECUPERACION[2]="Replaneación (2~Hz)"
TIPO_FALLO_RECUPERACION[3]="Spin + BackUp"
TIPO_FALLO_RECUPERACION[4]="Abortar y reintentar"
TIPO_FALLO_RECUPERACION[5]="(ver observación)"

banner() {
    echo ""
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}  $1${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
}

verificar_nav2() {
    if ! ros2 service list 2>/dev/null | grep -q '/navigate_to_pose'; then
        echo -e "${RED}ERROR: Nav2 no está activo.${NC}"
        echo "  Lanzar primero launch_sim_all.sh o launch_mapeo_all.sh"
        exit 1
    fi
}

enviar_meta_sim() {
    local x=$1 y=$2 z=$3 qw=$4
    ros2 action send_goal /navigate_to_pose \
        nav2_msgs/action/NavigateToPose \
        "{pose: {header: {frame_id: 'map'}, pose: {position: {x: ${x}, y: ${y}, z: ${z}}, orientation: {w: ${qw}, x: 0.0, y: 0.0, z: 0.0}}}}" \
        --feedback 2>&1
}

monitorear_goal() {
    local timeout=$1
    local t_start
    t_start=$(date +%s%3N)

    local tmpfile
    tmpfile=$(mktemp /tmp/nav_result.XXXXXX)

    if [ "$MODO" = "sim" ]; then
        local esc=$2
        local coords
        read -r coords <<< "${POSES_SIM[$esc]}"
        read -r xp yp zp qwp <<< "$coords"
        enviar_meta_sim "$xp" "$yp" "$zp" "$qwp" > "$tmpfile" 2>&1 &
    else
        echo -e "    ${YELLOW}→ Envía la meta desde RViz ahora (2D Nav Goal)...${NC}"
        echo -e "    ${YELLOW}   Esperando goal activo en /navigate_to_pose...${NC}"
        ros2 topic echo /navigate_to_pose/_action/status --once \
            > "$tmpfile" 2>&1 &
    fi

    local bg_pid=$!
    local elapsed=0
    local resultado="TIMEOUT"

    while [ $elapsed -lt $timeout ]; do
        sleep 2
        elapsed=$(( elapsed + 2 ))
        if ! kill -0 $bg_pid 2>/dev/null; then
            if grep -q "Goal accepted" "$tmpfile" &&                grep -q "Result:" "$tmpfile"; then
                resultado="EXITO"
            elif grep -qE "aborted|ABORTED|failed|FAILED|canceled|CANCELED" "$tmpfile"; then
                resultado="FALLO"
            elif grep -q "status: 4" "$tmpfile"; then   # SUCCEEDED (action_msgs)
                resultado="EXITO"
            elif grep -q "status: 5\|status: 6" "$tmpfile"; then  # CANCELED/ABORTED
                resultado="FALLO"
            fi
            break
        fi

        if [ "$MODO" = "real" ]; then
            local status_now
            status_now=$(ros2 topic echo /navigate_to_pose/_action/status                 --once 2>/dev/null | grep "status:" | tail -1 || true)
            if echo "$status_now" | grep -q "status: 4"; then
                resultado="EXITO"; kill $bg_pid 2>/dev/null || true; break
            elif echo "$status_now" | grep -q "status: 5\|status: 6"; then
                resultado="FALLO"; kill $bg_pid 2>/dev/null || true; break
            fi
        fi
        printf "\r    ⏳ Esperando resultado... [%ds/%ds]" "$elapsed" "$timeout"
    done
    echo ""

    kill $bg_pid 2>/dev/null || true
    wait $bg_pid 2>/dev/null || true

    local t_end
    t_end=$(date +%s%3N)
    local tiempo_ms=$(( t_end - t_start ))
    local tiempo_s
    tiempo_s=$(awk "BEGIN {printf \"%.1f\", $tiempo_ms/1000}")

    echo "$resultado $tiempo_s" > /tmp/nav_rep_result.txt
    rm -f "$tmpfile"

    [ "$resultado" = "EXITO" ] && return 0 || return 1
}

iniciar_csv() {

    echo "escenario,nombre_escenario,repeticion,resultado,tiempo_s,tipo_fallo,recuperacion_activada,exito_recuperacion,observaciones" \
        > "$CSV_OUT"
    echo -e "  Resultados: ${CYAN}${CSV_OUT}${NC}"
}

registrar_resultado() {
    local esc=$1 rep=$2 resultado=$3 tiempo=$4 tipo_fallo=$5 \
          recuperacion=$6 exito_rec=$7 obs=$8
    echo "${esc},\"${NOMBRES[$esc]}\",${rep},${resultado},${tiempo},\"${tipo_fallo}\",\"${recuperacion}\",\"${exito_rec}\",\"${obs}\"" \
        >> "$CSV_OUT"
}

solicitar_tipo_fallo() {
    echo ""
    echo -e "    ${RED}Clasificar tipo de fallo:${NC}"
    for opt in "${TIPO_FALLO_OPCIONES[@]}"; do
        echo -e "      $opt"
    done
    echo -n "    Número [1-5, Enter=5]: "
    local num
    read -r -t 20 num || num=5
    [[ "$num" =~ ^[1-5]$ ]] || num=5

    local clave="${TIPO_FALLO_KEY[$num]}"
    local rec="${TIPO_FALLO_RECUPERACION[$num]}"

    echo -n "    ¿La recuperación Nav2 resolvió el bloqueo? [s/N]: "
    local resp_rec
    read -r -t 10 resp_rec || resp_rec="n"
    local exito_rec="No"
    [[ "$resp_rec" == "s" || "$resp_rec" == "S" ]] && exito_rec="Sí"

    _TIPO_FALLO="$clave"
    _RECUPERACION="$rec"
    _EXITO_REC="$exito_rec"
}

generar_latex() {
    python3 - <<'PYEOF'
import csv, os, math, collections
from datetime import datetime

csv_path   = os.environ.get('CSV_OUT', '')
modo       = os.environ.get('MODO', 'sim')
tex_path   = os.environ.get('TEX_OUT', '')
tex_fallos = os.environ.get('TEX_FALLOS', '')
tolerancia = os.environ.get('TOLERANCIA', '0.22')

label   = f'nav_{modo}'
caption = (f'Resultados de navegación autónoma en simulación (5 repeticiones por escenario).'
           if modo == 'sim' else
           f'Resultados de navegación autónoma en hardware real (5 repeticiones por escenario).')

escenarios = {}
fallos_por_tipo = collections.defaultdict(lambda: {
    'count': 0, 'recuperacion': '', 'exitos_rec': 0
})

with open(csv_path) as f:
    for row in csv.DictReader(f):
        esc  = int(row['escenario'])
        name = row['nombre_escenario']
        if esc not in escenarios:
            escenarios[esc] = {'nombre': name, 'tiempos': [], 'exitos': 0, 'fallos': 0}
        if row['resultado'] == 'EXITO':
            escenarios[esc]['exitos'] += 1
            try:
                escenarios[esc]['tiempos'].append(float(row['tiempo_s']))
            except Exception:
                pass
        elif row['resultado'] in ('FALLO', 'TIMEOUT'):
            escenarios[esc]['fallos'] += 1

            tf = row.get('tipo_fallo', 'otro') or 'otro'
            rec = row.get('recuperacion_activada', '') or ''
            er  = row.get('exito_recuperacion', '') or ''
            fallos_por_tipo[tf]['count'] += 1
            fallos_por_tipo[tf]['recuperacion'] = rec
            if er == 'Sí':
                fallos_por_tipo[tf]['exitos_rec'] += 1

def stats(times):
    if not times:
        return '---', '---'
    mu = sum(times)/len(times)
    sigma = math.sqrt(sum((t-mu)**2 for t in times)/max(1,len(times)-1))
    return f'{mu:.1f}', f'{sigma:.1f}'

lines = [
    f'% Generado por run_prueba_nav.sh — {datetime.now().strftime("%Y-%m-%d %H:%M")}',
    f'% Tolerancia xy_goal_tolerance = {tolerancia} m ({modo})',
    r'\begin{table}[H]',
    r'\centering',
    f'\\caption{{{caption}}}',
    f'\\label{{tab:{label}}}',
    r'\begin{tabular}{lccccc}',
    r'\hline',
    r'\textbf{Escenario} & \textbf{Éxitos} & \textbf{Fallos} & \textbf{Tasa (\%)} & $\bar{t}$ (s) & $\sigma_t$ (s) \\',
    r'\hline',
]

tot_ex = tot_fa = 0
for esc in sorted(escenarios):
    d    = escenarios[esc]
    ex   = d['exitos']; fa = d['fallos']
    tot  = ex + fa
    tasa = f'{ex/tot*100:.0f}' if tot > 0 else '---'
    t_m, t_s = stats(d['tiempos'])
    tot_ex += ex; tot_fa += fa
    lines.append(f"{d['nombre']} & {ex} & {fa} & {tasa} & {t_m} & {t_s} \\\\")

lines.append(r'\hline')
tot_t    = tot_ex + tot_fa
tot_tasa = f'{tot_ex/tot_t*100:.0f}' if tot_t > 0 else '---'
lines.append(f'\\textbf{{Total}} & {tot_ex} & {tot_fa} & {tot_tasa} & --- & --- \\\\')
lines.append(r'\hline')
lines.append(r'\end{tabular}')
lines.append(f'% Nota: tolerancia de llegada = {tolerancia} m (\\texttt{{xy\\_goal\\_tolerance}})')
lines.append(r'\end{table}')

with open(tex_path, 'w') as f:
    f.write('\n'.join(lines))
print(f'  ✓ LaTeX navegación: {tex_path}')

LABEL_FALLO = {
    'costmap_bloqueado':  'Costmap bloqueado',
    'ruta_invalida':      "Ruta inválida",
    'robot_atascado':     'Robot atascado',
    'timeout_oscilacion': 'Timeout de navegación',
    'otro':               'Otro',
}
CAUSA_FALLO = {
    'costmap_bloqueado':  "Obstáculo no mapeado",
    'ruta_invalida':      "Espacio muy estrecho",
    'robot_atascado':     "Deslizamiento en giro",
    'timeout_oscilacion': "Oscilación local",
    'otro':               "Ver observación",
}
REC_TEX = {
    'ClearCostmapAroundRobot': r'\texttt{ClearCostmapAroundRobot}',
    'Replaneación (2~Hz)':     r'Replaneación (2~Hz)',
    'Spin + BackUp':           r'\texttt{Spin} + \texttt{BackUp}',
    'Abortar y reintentar':    'Abortar y reintentar',
    '(ver observación)':       '(ver observación)',
}

flines = [
    f'% Generado por run_prueba_nav.sh — {datetime.now().strftime("%Y-%m-%d %H:%M")}',
    r'\begin{table}[H]',
    r'\centering',
    r'\caption{Tipos de fallo observados durante la navegación y recuperaciones activadas.}',
    r'\label{tab:fallos_nav}',
    r'\begin{tabular}{llll}',
    r'\hline',
    r'\textbf{Tipo de fallo} & \textbf{Causa probable} & \textbf{Recuperación} & \textbf{Resultado} \\',
    r'\hline',
]

orden = ['costmap_bloqueado', 'ruta_invalida', 'robot_atascado', 'timeout_oscilacion', 'otro']
total_fallos = 0
for tf in orden:
    if tf in fallos_por_tipo:
        d   = fallos_por_tipo[tf]
        n   = d['count']
        rec_raw = d.get('recuperacion', '') or REC_TEX.get(tf, '---')
        rec_tex = REC_TEX.get(rec_raw, rec_raw) if rec_raw else '---'
        er  = d['exitos_rec']
        er_str = f'{er}/{n}' if n > 0 else '---'
        resultado_str = (f'Resuelto ({er}/{n})' if n > 0 and er == n
                          else f'Parcial ({er}/{n})' if n > 0 and er > 0
                          else f'No resuelto ({n} casos)' if n > 0
                          else '---')
        flines.append(
            f"{LABEL_FALLO.get(tf, tf)} & {CAUSA_FALLO.get(tf, '---')} & {rec_tex} & {resultado_str} \\\\"
        )
        total_fallos += n

if total_fallos == 0:
    for tf in orden:
        flines.append(
            f"{LABEL_FALLO.get(tf, tf)} & {CAUSA_FALLO.get(tf, '---')} & --- & Sin observaciones \\\\"
        )

flines.append(r'\hline')
flines.append(r'\end{tabular}')
flines.append(r'\vspace{4pt}')
flines.append(r'\begin{minipage}{\linewidth}')
flines.append(r'\footnotesize')
flines.append(r'\textbf{N} = número de ocurrencias observadas. \textbf{Rec.\ exitosa} = casos en que la recuperación Nav2 resolvió el bloqueo sin intervención manual.')
flines.append(r'\end{minipage}')
flines.append(r'\end{table}')

with open(tex_fallos, 'w') as f:
    f.write('\n'.join(flines))
print(f'  ✓ LaTeX fallos:     {tex_fallos}')
PYEOF
}

confirmar() {
    local msg="$1"
    echo -e "\n${YELLOW}>>> ${msg}${NC}"
    echo -n "    Presiona ENTER cuando esté listo (o 's' para saltear): "
    read -r resp
    [[ "$resp" == "s" || "$resp" == "S" ]] && return 1
    return 0
}

banner "PRUEBAS DE NAVEGACIÓN NAV2 — modo: ${MODO^^}"
echo -e "  ${BOLD}Escenarios:${NC}"
echo -e "    1. ${NOMBRES[1]}"
echo -e "    2. ${NOMBRES[2]}"
echo -e "    3. ${NOMBRES[3]}"
echo -e "  Repeticiones por escenario: ${REPS}"
echo -e "  Timeout por meta:           ${TIMEOUT_META} s"
echo -e "  Tolerancia de llegada:      ${TOLERANCIA} m (xy_goal_tolerance, modo ${MODO})\n"

if [ "$MODO" = "sim" ]; then
    echo -e "  ${YELLOW}PREREQUISITO: launch_sim_all.sh debe estar corriendo.${NC}"
    echo -e "  ${YELLOW}SLAM + Nav2 deben haber construido un mapa básico del entorno.${NC}\n"
else
    echo -e "  ${YELLOW}PREREQUISITO: launch_mapeo_all.sh debe estar corriendo.${NC}"
    echo -e "  ${YELLOW}El robot debe estar localizado en el mapa ya construido.${NC}\n"
fi

confirmar "¿El sistema está listo? Verificar: /map, Nav2, RViz activos." || {
    echo "Abortado."
    exit 0
}

verificar_nav2
iniciar_csv

TOTAL_EXITOS=0
TOTAL_INTENTOS=0

for ESC in 1 2 3; do
    banner "ESCENARIO ${ESC}/3: ${NOMBRES[$ESC]}"

    if [ "$MODO" = "sim" ]; then
        echo -e "  Pose objetivo: ${POSES_SIM[$ESC]}"
    else
        echo -e "  ${YELLOW}Preparar escenario físico antes de cada repetición.${NC}"
        case $ESC in
            2) echo -e "  ${YELLOW}Colocar un obstáculo (caja) entre el robot y la meta.${NC}" ;;
            3) echo -e "  ${YELLOW}La meta debe estar en zona estrecha o requiere giro en pasillo.${NC}" ;;
        esac
    fi

    for REP in $(seq 1 $REPS); do
        echo ""
        echo -e "  ${BOLD}── Repetición ${REP}/${REPS} ──────────────────────────────────${NC}"

        if [ "$MODO" = "real" ]; then
            confirmar "Posicionar robot en punto de inicio. Verificar en RViz." || {
                registrar_resultado "$ESC" "$REP" "SALTADA" "0" "" "" "" "Saltada por operador"
                continue
            }
        else

            echo -e "    ${CYAN}Reseteando robot a posición inicial (-1.5, -1.0)...${NC}"
            ros2 service call /set_entity_state gazebo_msgs/srv/SetEntityState                 "{state: {name: 'my_bot', pose: {position: {x: -1.5, y: -1.0, z: 0.05},                 orientation: {w: 1.0, x: 0.0, y: 0.0, z: 0.0}},                 twist: {linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}},                 reference_frame: 'world'}}" > /dev/null 2>&1 || true
            sleep 1

            ros2 service call /global_costmap/clear_entirely_global_costmap                 nav2_interfaces/srv/ClearEntireCostmap "{}" > /dev/null 2>&1 || true
            ros2 service call /local_costmap/clear_entirely_local_costmap                 nav2_interfaces/srv/ClearEntireCostmap "{}" > /dev/null 2>&1 || true
            sleep 2  # Esperar que SLAM re-localice
        fi

        echo -e "    ${GREEN}Enviando meta al robot...${NC}"

        _TIPO_FALLO=""
        _RECUPERACION=""
        _EXITO_REC=""
        OBS=""

        if monitorear_goal "$TIMEOUT_META" "$ESC"; then
            read -r RESULTADO TIEMPO_S < /tmp/nav_rep_result.txt
            RESULTADO="EXITO"
            echo -e "    ${GREEN}✓ META ALCANZADA en ${TIEMPO_S} s${NC}"
            TOTAL_EXITOS=$(( TOTAL_EXITOS + 1 ))
        else
            read -r RESULTADO TIEMPO_S < /tmp/nav_rep_result.txt 2>/dev/null || {
                RESULTADO="TIMEOUT"
                TIEMPO_S="$TIMEOUT_META"
            }
            echo -e "    ${RED}✗ FALLO: ${RESULTADO} en ${TIEMPO_S} s${NC}"

            ros2 topic pub --once /diff_cont/cmd_vel_unstamped \
                geometry_msgs/msg/Twist \
                '{linear: {x: 0.0}, angular: {z: 0.0}}' > /dev/null 2>&1 || true

            solicitar_tipo_fallo
        fi

        TOTAL_INTENTOS=$(( TOTAL_INTENTOS + 1 ))

        echo -n "    Observación libre (Enter para omitir): "
        read -r -t 15 OBS || OBS=""

        registrar_resultado "$ESC" "$REP" "$RESULTADO" "$TIEMPO_S" \
            "$_TIPO_FALLO" "$_RECUPERACION" "$_EXITO_REC" "$OBS"

        if [ "$REP" -lt "$REPS" ]; then
            echo -e "    ${YELLOW}Esperando 5 s antes de la siguiente repetición...${NC}"
            sleep 5
        fi
    done

    echo ""
    echo -e "  ${CYAN}Escenario ${ESC} completado.${NC}"
    if [ "$ESC" -lt 3 ]; then
        confirmar "Preparar escenario siguiente. ¿Continuar?" || break
    fi
done

banner "RESULTADOS FINALES"
TASA_TOTAL=0
if [ "$TOTAL_INTENTOS" -gt 0 ]; then
    TASA_TOTAL=$(awk "BEGIN {printf \"%.0f\", $TOTAL_EXITOS/$TOTAL_INTENTOS*100}")
fi

echo -e "  Éxitos totales:   ${TOTAL_EXITOS} / ${TOTAL_INTENTOS}"
echo -e "  Tasa de éxito:    ${TASA_TOTAL}%"
echo -e "  Datos guardados:  ${CSV_OUT}"

echo -e "\n  ${CYAN}Generando tablas LaTeX...${NC}"
export CSV_OUT MODO TEX_OUT TEX_FALLOS TOLERANCIA
generar_latex

echo ""
echo -e "  ${GREEN}✓ Tabla navegación:${NC} ${TEX_OUT}"
echo -e "  ${GREEN}✓ Tabla fallos:${NC}     ${TEX_FALLOS}"
echo ""
echo -e "  ${BOLD}Para la tesis:${NC}"
echo -e "    ${TEX_OUT}    → reemplazar tab:nav_${MODO}"
echo -e "    ${TEX_FALLOS} → reemplazar tab:fallos_nav"
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"