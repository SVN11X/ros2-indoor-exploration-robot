#!/usr/bin/env bash
# =============================================================================
# run_prueba_giro_sim.sh
# =============================================================================
# Prueba de giro 360° en SIMULACIÓN.
# bash ~/tesis_black_robot/experiments/prueba_giro_sim/run_prueba_giro_sim.sh
# Estrategia: UNA sesión de Gazebo para todas las pruebas.
# Entre pruebas el robot se teletransporta a x=0, y=0, yaw=0 via
# /set_entity_state (plugin gazebo_ros_state en giro.world).
# NO se reinicia Gazebo entre pruebas — solo se resetea la pose.
#
# Diferencia clave con linea_recta_sim:
#   - linea_recta: robot avanza ~2 m/prueba, no vuelve al origen
#     (el pasillo tiene espacio suficiente)
#   - giro: robot gira en el mismo punto, pero pequeño drift lineal
#     acumulado requiere resetear la pose antes de cada prueba
#     para mantener condiciones iniciales idénticas.
#
# Flujo:
#   1. Limpieza completa + lanzar Gazebo + robot  (UNA sola vez)
#   2. Verificar disponibilidad de /set_entity_state
#   3. Bucle N_PRUEBAS veces:
#        a. Resetear pose (x=0, y=0, yaw=0) via /set_entity_state
#        b. Grabar rosbag
#        c. Ejecutar prueba_giro_sim.py
#        d. Pausa de estabilización
#   4. Limpieza final + análisis
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS="${HOME}/tesis_black_robot"
CONFIG="${WS}/src/articubot_one/config"
WORLD="${WS}/src/articubot_one/worlds/giro.world"
N_PRUEBAS=5
SPAWN_X="0.0"; SPAWN_Y="0.0"; SPAWN_Z="0.05"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

START_GLOBAL=$(date +%s)
elapsed_global() { echo $(( $(date +%s) - START_GLOBAL )); }

# ── wait_for — idéntico al de linea_recta_sim ────────────────────────────────
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
            return 0   # no propagar falla — set -e mataría el script
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
echo -e "${CYAN} Prueba Giro 360° — SIMULACIÓN${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e " World  : ${BOLD}giro.world${NC} (plugin gazebo_ros_state)"
echo -e " Centro : x=0, y=0, yaw=0 — reset via /set_entity_state"
echo -e " Sin SLAM ni Nav2 — solo odometría"
echo -e " ${BOLD}Sesión única de Gazebo — reset de pose entre pruebas${NC}"
echo ""

[ ! -f "${WORLD}" ] && {
    echo -e "${RED}ERROR: ${WORLD} no encontrado${NC}"; exit 1; }

# =============================================================================
# FUNCIÓN: limpiar_todo
# Idéntica a linea_recta_sim — sesión 100% limpia al inicio
# =============================================================================
limpiar_todo() {
    echo -e "${YELLOW}── Limpiando procesos anteriores... ─────────────────${NC}"
    rm -f /tmp/sim_ready /tmp/sim_nav2_ready /tmp/sim_world
    rm -f /tmp/gazebo_launch.log /tmp/slam_launch.log /tmp/nav2_launch.log
    rm -f /tmp/bag_slam_sim.log /tmp/gazebo_giro.log

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
    pkill -9 -f "launch_sim_all"           2>/dev/null || true
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
# Idéntica a linea_recta_sim pero con giro.world y spawn en x=0, y=0
# NO lanza SLAM ni Nav2 — solo Gazebo + robot (suficiente para odometría)
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
        world:="${WORLD}" > /tmp/gazebo_giro.log 2>&1 &
    PID_SIM=$!
    echo "${PID_SIM}" > /tmp/pid_sim_giro

    wait_for "Gazebo publicando /clock" 60 \
        "ros2 topic list 2>/dev/null | grep -q '/clock'"

    # Verificar spawn
    sleep 8
    if ! grep -q 'Successfully spawned' /tmp/gazebo_giro.log 2>/dev/null; then
        if grep -q 'already exists' /tmp/gazebo_giro.log 2>/dev/null; then
            echo -e "${GREEN} ✓ Robot ya existía (reutilizando)${NC}"
        else
            echo -e "${YELLOW} Spawn falló — reintentando manualmente...${NC}"
            wait_for "Servicio /spawn_entity" 30 \
                "ros2 service list 2>/dev/null | grep -q '/spawn_entity'"
            ros2 run gazebo_ros spawn_entity.py \
                -topic robot_description -entity my_bot \
                -x "${SPAWN_X}" -y "${SPAWN_Y}" -z "${SPAWN_Z}" \
                >> /tmp/gazebo_giro.log 2>&1
        fi
    fi

    wait_for "Controladores diff_cont activos" 40 \
        "ros2 control list_controllers 2>/dev/null | grep -q 'active'"

    # Verificar que diff_cont realmente está activo antes de continuar
    if ! timeout 3 ros2 control list_controllers 2>/dev/null | grep -q 'active'; then
        echo -e "${RED} ERROR CRÍTICO: diff_cont no está activo.${NC}"
        echo -e "${YELLOW} Verifica:  cat /tmp/gazebo_giro.log | grep -i 'error\|warn\|control'${NC}"
        exit 1
    fi

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
# FUNCIÓN: resetear_pose
# Teletransporta el robot a x=0, y=0, yaw=0 via /set_entity_state.
# Necesario entre pruebas de giro porque el robot acumula pequeño drift
# lineal aunque gire en el mismo punto.
# =============================================================================
SERVICIO_OK=false

verificar_servicio_reset() {
    echo -ne "${YELLOW} Esperando /set_entity_state${NC}"
    for i in $(seq 1 40); do
        if timeout 3 ros2 service list 2>/dev/null | grep -q "set_entity_state"; then
            echo -e " ${GREEN}✓ disponible${NC}"
            SERVICIO_OK=true
            return 0
        fi
        sleep 2; echo -ne "."
    done
    echo ""
    echo -e "${RED} ✗ /set_entity_state no encontrado.${NC}"
    echo ""
    echo -e "${YELLOW} DIAGNÓSTICO:${NC}"
    echo "   ros2 service list | grep entity"
    echo "   grep -i 'gazebo_ros_state' /tmp/gazebo_giro.log | tail -5"
    echo ""
    echo -e "${YELLOW} CAUSA PROBABLE:${NC}"
    echo "   giro.world debe tener el plugin libgazebo_ros_state.so"
    echo ""
    echo -e "${YELLOW} SOLUCIÓN MANUAL:${NC}"
    echo "   Posiciona el robot en el centro usando Gazebo GUI:"
    echo "   Edit → Move Model → my_bot → x=0, y=0"
    echo ""
    read -rp " Presiona ENTER para continuar sin reset automático..."
}

resetear_pose() {
    if [ "${SERVICIO_OK}" = false ]; then
        echo -e "${YELLOW}   (sin servicio — posiciona manualmente el robot)${NC}"
        read -rp "   Presiona ENTER cuando el robot esté en x=0, y=0..."
        return 0
    fi
    for i in $(seq 1 10); do
        if timeout 10 ros2 service call /set_entity_state \
            gazebo_msgs/srv/SetEntityState \
            "{state: {name: 'my_bot',
              pose: {position:    {x: ${SPAWN_X}, y: ${SPAWN_Y}, z: ${SPAWN_Z}},
                     orientation: {x: 0.0, y: 0.0, z: 0.0, w: 1.0}},
              reference_frame: 'world'}}" > /dev/null 2>&1; then
            echo -e "${GREEN}   ✓ Pose reseteada (x=0, y=0, yaw=0)${NC}"
            # Detener ruedas residuales
            timeout 5 ros2 topic pub --once /diff_cont/cmd_vel_unstamped \
                geometry_msgs/msg/Twist "{}" > /dev/null 2>&1 || true
            sleep 1
            return 0
        fi
        echo -e "${YELLOW}   Intento ${i}/10...${NC}"; sleep 3
    done
    echo -e "${RED}   ✗ Reset falló — continúa con posición actual${NC}"
}

# =============================================================================
# INICIO: Limpieza única + lanzamiento único de Gazebo
# =============================================================================
echo -e "${CYAN}── Preparación inicial (única sesión de Gazebo) ─────${NC}"
limpiar_todo
lanzar_gazebo_robot

# Verificar disponibilidad de /set_entity_state (plugin gazebo_ros_state)
verificar_servicio_reset

# Pausa inicial para que el robot se estabilice físicamente
echo -e "${YELLOW} Estabilizando robot antes de la primera prueba (3s)...${NC}"
sleep 3

# =============================================================================
# BUCLE PRINCIPAL: reset de pose + grabación + prueba
# Gazebo sigue corriendo entre pruebas — solo se teletransporta el robot.
# =============================================================================
for N in $(seq 1 ${N_PRUEBAS}); do
    echo ""
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN} PRUEBA ${N} de ${N_PRUEBAS}  (t+$(elapsed_global)s)${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"

    # 1. Resetear pose al centro (diferencia con linea_recta_sim)
    echo -e "${YELLOW} Reseteando pose (x=0, y=0, yaw=0)...${NC}"
    resetear_pose

    # 2. Grabar rosbag
    BAG_DIR="${SCRIPT_DIR}/prueba_giro_sim_${N}"
    rm -rf "${BAG_DIR}"
    ros2 bag record /odom /tf -o "${BAG_DIR}" \
        > /tmp/rosbag_giro_sim.log 2>&1 &
    BAG_PID=$!
    sleep 1

    # 3. Ejecutar giro
    echo -e " Giro 360° (ω=0.4 rad/s, ~15.7 s)..."
    python3 "${SCRIPT_DIR}/prueba_giro_sim.py" --prueba "${N}" \
        > /tmp/prueba_giro_sim_live.log 2>&1 || {
        echo -e "${YELLOW} AVISO: error en prueba${NC}"
        timeout 5 ros2 topic pub --once /diff_cont/cmd_vel_unstamped \
            geometry_msgs/msg/Twist "{}" > /dev/null 2>&1 || true
    }

    # 4. Detener rosbag
    sleep 0.5
    kill "${BAG_PID}" 2>/dev/null || true
    wait "${BAG_PID}" 2>/dev/null || true

    # 5. Resultado
    echo ""
    grep -E "Giro|Deriva|RESULTADOS" \
        /tmp/prueba_giro_sim_live.log | sed 's/.*\] /  /' || true

    # 6. Pausa entre pruebas: deja al robot detenerse completamente
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
python3 "${SCRIPT_DIR}/analizar_prueba_giro_sim.py"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo -e "${GREEN} LISTO — Archivos en ${SCRIPT_DIR}/${NC}"
echo -e "   prueba_giro_sim_{1..${N_PRUEBAS}}.log"
echo -e "   tabla_odom_giro_sim.tex  ← tab:odom_giro_sim"
echo -e "   giro_deriva_sim.png      ← figura tesis"
echo -e "${GREEN}═══════════════════════════════════════════════════${NC}"
echo ""