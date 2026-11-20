#!/usr/bin/env bash
# =============================================================================
# run_prueba_recta_sim.sh
# =============================================================================
# Prueba de trayectoria rectilínea en SIMULACIÓN.
#
# Estrategia: UNA sesión de Gazebo para todas las pruebas.
# El robot avanza 2 m por prueba sin volver al origen.
# El pasillo tiene ~13.5 m de recorrido útil desde el spawn (x=-1.5),
# por lo que N_PRUEBAS=5 (5 × 2 m = 10 m) cabe holgadamente.
#
# Flujo:
#   1. Limpieza completa + lanzar Gazebo + robot  (UNA sola vez)
#   2. Bucle N_PRUEBAS veces:
#        a. Grabar rosbag
#        b. Ejecutar prueba_recta_sim.py  (robot avanza desde donde quedó)
#        c. Pausa breve de estabilización
#   3. Limpieza final + análisis
#
# NOTA: Si necesitas más de 6 pruebas, reduce la distancia por prueba o
# aumenta el pasillo en linea_recta.world (pared derecha en x=12.0).
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="${HOME}/tesis_black_robot"
CONFIG="${WS}/src/articubot_one/config"
WORLD="${WS}/src/articubot_one/worlds/linea_recta.world"
N_PRUEBAS=5

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

START_GLOBAL=$(date +%s)
elapsed_global() { echo $(( $(date +%s) - START_GLOBAL )); }

# ── wait_for — idéntico al de launch_sim_all.sh ──────────────────────────────
wait_for() {
    local desc="$1" timeout="$2"; shift 2
    local start=$(date +%s)
    while true; do
        local elapsed=$(( $(date +%s) - start ))
        if timeout 3 bash -c "$*" > /dev/null 2>&1; then
            printf "\r${GREEN} ✓ %-45s [%3ds]${NC}\n" "$desc" "$elapsed"
            return 0
        fi
        if [ $elapsed -ge $timeout ]; then
            printf "\r${RED} ✗ %-45s [TIMEOUT]${NC}\n" "$desc"
            echo -e "${YELLOW} Continuando de todos modos...${NC}"
            return 1
        fi
        printf "\r${YELLOW} ⏳ %-45s [%3ds/%ds]${NC}" "$desc" "$elapsed" "$timeout"
        sleep 2
    done
}

# ── Fuente ROS2 ───────────────────────────────────────────────────────────────
set +u
source /opt/ros/foxy/setup.bash
source "${WS}/install/setup.bash" 2>/dev/null || \
source "${HOME}/dev_ws/install/setup.bash" 2>/dev/null || \
{ echo "ERROR: no se encontró install/setup.bash"; exit 1; }
set -u

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN} Prueba Línea Recta — SIMULACIÓN${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e " World  : ${BOLD}linea_recta.world${NC}"
echo -e " Spawn  : x=-1.5, y=-1.0, yaw=0  (apuntando a +X)"
echo -e " Pasillo: x=-2.5 → x=12.0  (recorrido útil ≈ 13.5 m)"
echo -e " Sin SLAM ni Nav2 — solo odometría"
echo -e " ${BOLD}Sesión única de Gazebo — robot avanza sin volver al origen${NC}"
echo -e " ${N_PRUEBAS} pruebas × 2 m = $(( N_PRUEBAS * 2 )) m total  (límite pasillo: ≈13.5 m)"
echo ""

[ ! -f "${WORLD}" ] && {
    echo -e "${RED}ERROR: ${WORLD} no encontrado${NC}"; exit 1; }

# Advertencia si el recorrido total se acerca al límite del pasillo
RECORRIDO_TOTAL=$(( N_PRUEBAS * 2 ))
if [ "${RECORRIDO_TOTAL}" -gt 12 ]; then
    echo -e "${RED}ADVERTENCIA: ${RECORRIDO_TOTAL} m de recorrido puede salir del pasillo.${NC}"
    echo -e "${RED}Reduce N_PRUEBAS o la distancia en prueba_recta_sim.py.${NC}"
    echo ""
fi

# =============================================================================
# FUNCIÓN: limpiar_todo
# Copia exacta de los pasos 0-6 de launch_sim_all.sh
# =============================================================================
limpiar_todo() {
    echo -e "${YELLOW}── Limpiando procesos anteriores... ─────────────────${NC}"
    rm -f /tmp/sim_ready /tmp/sim_nav2_ready
    rm -f /tmp/gazebo_launch.log /tmp/slam_launch.log /tmp/nav2_launch.log
    rm -f /tmp/bag_slam_sim.log /tmp/gazebo_recta.log

    # Paso 1: Eliminar entidad my_bot si Gazebo corre
    if timeout 3 ros2 topic list 2>/dev/null | grep -q '/clock'; then
        echo -e "${YELLOW} Gazebo activo — eliminando my_bot...${NC}"
        timeout 5 ros2 service call /delete_entity gazebo_msgs/srv/DeleteEntity \
            "{name: 'my_bot'}" > /dev/null 2>/dev/null || true
        sleep 1
    fi

    # Paso 2: Procesos ROS2
    pkill -9 -f "ros2 bag record"          2>/dev/null || true
    pkill -9 -f "async_slam_toolbox_node"  2>/dev/null || true
    pkill -9 -f "nav2_bringup"             2>/dev/null || true
    pkill -9 -f "navigation_launch"        2>/dev/null || true
    pkill -9 -f "online_async_launch"      2>/dev/null || true
    pkill -9 -f "launch_sim.launch"        2>/dev/null || true
    pkill -9 -f "spawn_entity"             2>/dev/null || true
    killall -9 robot_state_publisher       2>/dev/null || true
    killall -9 twist_mux                   2>/dev/null || true
    killall -9 joy_node teleop_node        2>/dev/null || true
    killall -9 async_slam_toolbox_node     2>/dev/null || true
    killall -9 controller_server planner_server bt_navigator 2>/dev/null || true
    killall -9 recoveries_server waypoint_follower lifecycle_manager 2>/dev/null || true
    killall -9 rviz2                       2>/dev/null || true
    sleep 1

    # Paso 3: Gazebo
    pkill -9 -f "gzserver"  2>/dev/null || true
    pkill -9 -f "gzclient"  2>/dev/null || true
    pkill -9 -f "gazebo"    2>/dev/null || true
    killall -9 gzserver gzclient 2>/dev/null || true

    # Paso 4: Esperar muerte de gzserver (hasta 20s)
    GAZEBO_DEAD=false
    for i in $(seq 1 20); do
        if ! pgrep -x gzserver > /dev/null 2>&1; then
            echo -e "${GREEN} ✓ gzserver detenido [${i}s]${NC}"
            GAZEBO_DEAD=true; break
        fi
        sleep 1
    done
    if [ "$GAZEBO_DEAD" = false ]; then
        echo -e "${RED} gzserver no murió — forzando sudo...${NC}"
        sudo pkill -9 gzserver 2>/dev/null || true
        sleep 3
    fi

    # Paso 5: Limpiar cache Gazebo
    rm -rf ~/.gazebo/log/
    find /tmp -name "gazebo_*" -delete 2>/dev/null || true

    # Paso 6: ROS2 daemon limpio
    ros2 daemon stop 2>/dev/null || true
    sleep 2
    REMAINING=$(ros2 topic list 2>/dev/null | wc -l)
    if [ "$REMAINING" -gt 2 ]; then
        echo -e "${YELLOW} Quedan $REMAINING topics residuales, esperando...${NC}"
        sleep 3
    fi
    ros2 daemon start 2>/dev/null || true
    sleep 1

    echo -e "${GREEN} ✓ Limpieza completada${NC}"
}

# =============================================================================
# FUNCIÓN: lanzar_gazebo_robot
# Copia exacta del paso 1 de launch_sim_all.sh (sin SLAM ni Nav2)
# =============================================================================
lanzar_gazebo_robot() {
    # Limpiar my_bot embebido del world si quedó de sesión anterior
    python3 -c "
import re
with open('${WORLD}', 'r') as f: c = f.read()
c2 = re.sub(r\"<model name='my_bot'>.*?</model>\", '', c, flags=re.DOTALL)
with open('${WORLD}', 'w') as f: f.write(c2)
" 2>/dev/null || true

    echo -e "${GREEN}[1/1] Lanzando Gazebo + Robot...${NC}"
    ros2 launch articubot_one launch_sim.launch.py \
        world:="${WORLD}" > /tmp/gazebo_recta.log 2>&1 &
    PID_SIM=$!
    echo "${PID_SIM}" > /tmp/pid_sim_recta

    wait_for "Gazebo publicando /clock" 60 \
        "ros2 topic list 2>/dev/null | grep -q '/clock'"

    # Verificar spawn — igual que launch_sim_all.sh
    sleep 8
    if ! grep -q 'Successfully spawned' /tmp/gazebo_recta.log 2>/dev/null; then
        if grep -q 'already exists' /tmp/gazebo_recta.log 2>/dev/null; then
            echo -e "${GREEN} ✓ Robot ya existía (reutilizando)${NC}"
        else
            echo -e "${YELLOW} Spawn falló — reintentando manualmente...${NC}"
            wait_for "Servicio /spawn_entity" 30 \
                "ros2 service list 2>/dev/null | grep -q '/spawn_entity'"
            ros2 run gazebo_ros spawn_entity.py \
                -topic robot_description -entity my_bot \
                -x -1.5 -y -1.0 -z 0.05 >> /tmp/gazebo_recta.log 2>&1
        fi
    fi

    wait_for "Controladores diff_cont activos" 40 \
        "ros2 control list_controllers 2>/dev/null | grep -q 'active'"

    wait_for "Odometría /odom publicando" 30 \
        "ros2 topic list 2>/dev/null | grep -q '/odom'"

    wait_for "LiDAR /scan publicando" 30 \
        "ros2 topic list 2>/dev/null | grep -q '/scan'"

    wait_for "TF odom→base_link disponible" 30 \
        "ros2 run tf2_ros tf2_echo odom base_link 2>&1 | grep -q 'Translation'"

    # Lanzar Gazebo GUI y RViz para visualización
    gzclient > /dev/null 2>&1 &
    sleep 2
    ros2 run rviz2 rviz2 -d "${CONFIG}/main.rviz" > /dev/null 2>&1 &

    echo -e "${GREEN} ✓ Gazebo + Robot listos (GUI + RViz lanzados)${NC}"
    echo ""
}

# =============================================================================
# INICIO: Limpieza única + lanzamiento único de Gazebo
# El robot spawnea en x=-1.5, y=-1.0, yaw=0 y desde ahí avanza N veces.
# =============================================================================
echo -e "${CYAN}── Preparación inicial (única sesión de Gazebo) ─────${NC}"
limpiar_todo
lanzar_gazebo_robot

# Pausa inicial para que el robot se estabilice físicamente
echo -e "${YELLOW} Estabilizando robot antes de la primera prueba (3s)...${NC}"
sleep 3

# =============================================================================
# BUCLE PRINCIPAL: solo grabación + prueba
# Gazebo sigue corriendo entre pruebas — el robot parte desde donde quedó.
# =============================================================================
for N in $(seq 1 ${N_PRUEBAS}); do
    echo ""
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN} PRUEBA ${N} de ${N_PRUEBAS}  (t+$(elapsed_global)s)${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"

    # 1. Grabar rosbag
    BAG_DIR="${SCRIPT_DIR}/prueba_recta_sim_${N}"
    rm -rf "${BAG_DIR}"
    ros2 bag record /odom /tf -o "${BAG_DIR}" \
        > /tmp/rosbag_recta_sim.log 2>&1 &
    BAG_PID=$!
    sleep 1

    # 2. Ejecutar movimiento (robot avanza desde su posición actual)
    echo -e " Movimiento (v=0.13 m/s, 2.00 m teórico)..."
    python3 "${SCRIPT_DIR}/prueba_recta_sim.py" --prueba "${N}" \
        > /tmp/prueba_recta_sim_live.log 2>&1 || {
        echo -e "${YELLOW} AVISO: error en prueba${NC}"
        timeout 5 ros2 topic pub --once /diff_cont/cmd_vel_unstamped \
            geometry_msgs/msg/Twist "{}" > /dev/null 2>&1 || true
    }

    # 3. Detener rosbag
    sleep 0.5
    kill "${BAG_PID}" 2>/dev/null || true
    wait "${BAG_PID}" 2>/dev/null || true

    # 4. Resultado
    echo ""
    grep -E "dist_odom|dist_real|error_pct|RESULTADOS" \
        /tmp/prueba_recta_sim_live.log | sed 's/.*\] /  /' || true

    # 5. Pausa entre pruebas: deja al robot detenerse completamente
    if [ "${N}" -lt "${N_PRUEBAS}" ]; then
        echo -e "${YELLOW} Pausa entre pruebas (2s)...${NC}"
        sleep 2
    fi
done

# ─── Limpieza final ───────────────────────────────────────────────────────────
echo ""
echo -e "${YELLOW} Limpieza final...${NC}"
limpiar_todo

# ─── Análisis ─────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN} ANÁLISIS FINAL${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
python3 "${SCRIPT_DIR}/analizar_prueba_recta_sim.py"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN} LISTO — Archivos en ${SCRIPT_DIR}/${NC}"
echo -e "   prueba_recta_sim_{1..${N_PRUEBAS}}.log"
echo -e "   tabla_odom_recta_sim.tex   ← tab:odom_recta_sim"
echo -e "   odom_error_barras_sim.png  ← figura tesis"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""