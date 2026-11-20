#!/bin/bash

set -euo pipefail

WS=~/tesis_black_robot
CONFIG=$WS/src/articubot_one/config
TEST_DIR=$WS/experiments

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

START_GLOBAL=$(date +%s)
TIMESTAMP="actual"
PID_BAG=""
SKIP_BUILD=false

elapsed_global() { echo $(( $(date +%s) - START_GLOBAL )); }

wait_for() {
    local desc="$1"; local timeout="$2"; shift 2
    local start=$(date +%s)
    while true; do
        local elapsed=$(( $(date +%s) - start ))
        local global=$(elapsed_global)
        if timeout 8 bash -c "$*" > /dev/null 2>&1; then
            printf "\r${GREEN} ✓ %-45s [%3ds] (total: %ds)${NC}\n" "$desc" "$elapsed" "$global"
            return 0
        fi
        if [ $elapsed -ge $timeout ]; then
            printf "\r${RED} ✗ %-45s [TIMEOUT %ds]${NC}\n" "$desc" "$timeout"
            echo -e "${YELLOW} Continuando de todos modos...${NC}"
            return 1
        fi
        printf "\r${YELLOW} ⏳ %-45s [%3ds / %ds]${NC}" "$desc" "$elapsed" "$timeout"
        sleep 2
    done
}
WORLD_ARG=""
WORLD_NAME="obstacles"
while [[ $# -gt 0 ]]; do
    case "$1" in
        --world)
            WORLD_ARG="$2"
            WORLD_NAME="$(basename "${WORLD_ARG}" .world)"
            shift 2
            ;;
        --skip-build)
            SKIP_BUILD=true
            shift
            ;;
        *)
            echo "Argumento desconocido: $1"
            echo "Uso: $0 [--world RUTA_WORLD] [--skip-build]"
            exit 1
            ;;
    esac
done
if [ -n "${WORLD_ARG}" ]; then
    if [[ "${WORLD_ARG}" = /* ]]; then
        WORLD_PATH="${WORLD_ARG}"
    else
        WORLD_PATH="${WS}/${WORLD_ARG}"
    fi
    if [ ! -f "${WORLD_PATH}" ]; then
        echo "ERROR: World no encontrado: ${WORLD_PATH}"
        exit 1
    fi
else
    WORLD_PATH="${WS}/src/articubot_one/worlds/obstacles.world"
fi

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN} Lanzamiento Simulación Robot Diferencial${NC}"
echo -e "${CYAN} World: ${BOLD}${WORLD_NAME}${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""
echo "${WORLD_PATH}" > /tmp/sim_world
rm -f /tmp/sim_ready /tmp/sim_nav2_ready
echo -e "${YELLOW}[0/4] Limpiando procesos anteriores...${NC}"
rm -f /tmp/gazebo_launch.log /tmp/slam_launch.log /tmp/nav2_launch.log /tmp/bag_slam_sim.log
if ros2 topic list 2>/dev/null | grep -q '/clock'; then
    echo -e "${YELLOW} Gazebo detectado, eliminando entidad my_bot...${NC}"
    timeout 5 ros2 service call /delete_entity gazebo_msgs/srv/DeleteEntity \
        "{name: 'my_bot'}" > /dev/null 2>&1 || true
    sleep 1
fi
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
pkill -9 -f "gzserver"  2>/dev/null || true
pkill -9 -f "gzclient"  2>/dev/null || true
pkill -9 -f "gazebo"    2>/dev/null || true
killall -9 gzserver gzclient 2>/dev/null || true
echo -e "${YELLOW} Esperando que gzserver termine...${NC}"
GAZEBO_DEAD=false
for i in $(seq 1 20); do
    if ! pgrep -x gzserver > /dev/null 2>&1; then
        echo -e "${GREEN} ✓ gzserver detenido [${i}s]${NC}"
        GAZEBO_DEAD=true
        break
    fi
    sleep 1
done
if [ "$GAZEBO_DEAD" = false ]; then
    echo -e "${RED} ✗ gzserver no murió en 20s, forzando con sudo...${NC}"
    sudo pkill -9 gzserver 2>/dev/null || true
    sleep 3
fi
rm -rf ~/.gazebo/log/
find /tmp -name "gazebo_*" -delete 2>/dev/null || true
ros2 daemon stop 2>/dev/null || true
sleep 2
REMAINING=$(ros2 topic list 2>/dev/null | wc -l)
if [ "$REMAINING" -gt 2 ]; then
    echo -e "${YELLOW} Aún quedan $REMAINING topics residuales, esperando...${NC}"
    sleep 3
fi
ros2 daemon start 2>/dev/null || true
sleep 1

echo -e "${GREEN} ✓ Limpieza completada${NC}"
cd $WS
if [ "${SKIP_BUILD}" = false ]; then
    echo -e "${YELLOW}[0/4] Compilando...${NC}"
    BUILD_START=$(date +%s)
    colcon build --symlink-install
    BUILD_TIME=$(( $(date +%s) - BUILD_START ))
    echo -e "${GREEN} ✓ Build completado [${BUILD_TIME}s]${NC}"
else
    echo -e "${YELLOW}[0/4] Compilación omitida (--skip-build)${NC}"
fi
set +u
source install/setup.bash
set -u
echo ""
GUARDAR_MAPA_PY="$TEST_DIR/utils/guardar_mapa.py"

if grep -q "model name='my_bot'" "${WORLD_PATH}" 2>/dev/null; then
    echo -e "${RED} ⚠ ADVERTENCIA: obstacles.world contiene my_bot embebido.${NC}"
    echo -e "${YELLOW} Limpiando world file...${NC}"
    python3 -c "
import re, sys
with open('${WORLD_PATH}', 'r') as f:
    content = f.read()
cleaned = re.sub(r\"<model name='my_bot'>.*?</model>\", '', content, flags=re.DOTALL)
with open('${WORLD_PATH}', 'w') as f:
    f.write(cleaned)
print(' World file limpiado.')
"
fi
echo -e "${GREEN}[1/4] Lanzando Gazebo + Robot...${NC}"
setsid ros2 launch articubot_one launch_sim.launch.py \
    world:="${WORLD_PATH}" > /tmp/gazebo_launch.log 2>&1 &
PID_SIM=$!

wait_for "Gazebo publicando /clock" 60 \
    "ros2 topic list 2>/dev/null | grep -q '/clock'"

sleep 8
if ! grep -q 'Successfully spawned' /tmp/gazebo_launch.log 2>/dev/null; then
    if grep -q 'already exists' /tmp/gazebo_launch.log 2>/dev/null; then
        echo -e "${GREEN} ✓ Robot ya existía en Gazebo (reutilizando)${NC}"
    else
        echo -e "${YELLOW} ⚠ Spawn falló, reintentando...${NC}"
        wait_for "Servicio /spawn_entity disponible" 30 \
            "ros2 service list 2>/dev/null | grep -q '/spawn_entity'"
        ros2 run gazebo_ros spawn_entity.py \
            -topic robot_description -entity my_bot \
            -x -1.5 -y -1.0 -z 0.05 >> /tmp/gazebo_launch.log 2>&1
    fi
fi

wait_for "Controladores diff_cont activos" 40 \
    "ros2 control list_controllers 2>/dev/null | grep -q 'active'"

wait_for "Odometría /odom publicando" 30 \
    "ros2 topic list 2>/dev/null | grep -q '/odom'"

wait_for "LiDAR publicando /scan" 30 \
    "ros2 topic list 2>/dev/null | grep -q '/scan'"
wait_for "TF odom->base_link disponible" 60 \
    "ros2 topic info /tf 2>/dev/null | grep -q 'Publisher count: [1-9]'"
echo ""
echo -e "${GREEN}[2/4] Lanzando SLAM Toolbox...${NC}"
setsid ros2 launch slam_toolbox online_async_launch.py \
    params_file:=$CONFIG/mapper_params_online_async_sim.yaml \
    use_sim_time:=true > /tmp/slam_launch.log 2>&1 &
PID_SLAM=$!

wait_for "SLAM publicando /map" 30 \
    "ros2 topic list 2>/dev/null | grep -q '/map'"
wait_for "TF map->odom disponible" 60 \
    "ros2 topic info /tf 2>/dev/null | grep -q 'Publisher count: [1-9]'"
echo ""
BAG_SLAM_DIR="${TEST_DIR}/slam/mapeo_sim"
rm -rf "${BAG_SLAM_DIR}"
mkdir -p "${TEST_DIR}/slam"
echo -e "${YELLOW} Iniciando grabación rosbag para analizar_slam.py...${NC}"
ros2 bag record \
    /odom /scan /tf /tf_static /map /clock \
    -o "${BAG_SLAM_DIR}" > /tmp/bag_slam_sim.log 2>&1 &
PID_BAG=$!
echo -e "${GREEN} ✓ Bag: ${BAG_SLAM_DIR}${NC}"
echo -e "${GREEN}[3/4] Lanzando Nav2...${NC}"
ros2 launch nav2_bringup navigation_launch.py \
    use_sim_time:=true \
    map_subscribe_transient_local:=true \
    params_file:=$CONFIG/nav2_params_sim.yaml > /tmp/nav2_launch.log 2>&1 &
PID_NAV=$!

wait_for "Nav2 lifecycle manager disponible" 45 \
    "ros2 service list 2>/dev/null | grep -q '/lifecycle_manager_navigation/is_active'"

wait_for "Nav2 costmaps activos" 60 \
    "ros2 service list 2>/dev/null | grep -q '/global_costmap/clear_entirely_global_costmap'"

wait_for "Action /navigate_to_pose disponible" 30 \
    "ros2 action list 2>/dev/null | grep -q '/navigate_to_pose'"
echo ""
touch /tmp/sim_ready
touch /tmp/sim_nav2_ready
echo "${TIMESTAMP}" > /tmp/sim_ready

TOTAL_TIME=$(elapsed_global)
echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN} ✓ SISTEMA LISTO - Puedes operar el robot${NC}"
echo -e "${GREEN} Tiempo total de arranque: ${TOTAL_TIME} segundos${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""
echo -e " ${BOLD}World activo: ${WORLD_NAME}${NC}"
echo ""
echo -e " ${BOLD}Tests habilitados ahora:${NC}"
echo -e "   test/linea_recta_sim/run_prueba_recta_sim.sh  ${GREEN}← /odom ✓${NC}"
echo -e "   test/prueba_giro_sim/run_prueba_giro_sim.sh   ${GREEN}← /odom ✓${NC}"
echo -e "   test/verificacion_tf/run_verificacion_tf.sh   ${GREEN}← /tf ✓${NC}"
echo -e "   test/navegacion/run_prueba_nav.sh sim         ${GREEN}← Nav2 ✓${NC}"
echo -e "   test/exploracion/run_explore.sh sim           ${GREEN}← Nav2+/map ✓${NC}"
echo ""
echo -e " ${BOLD}Grabando rosbag para analizar_slam.py:${NC}"
echo -e "   ${CYAN}${BAG_SLAM_DIR}${NC}"
echo -e "   (se detiene automáticamente al Ctrl+C)"
echo ""
echo -e " Logs: /tmp/gazebo_launch.log  /tmp/slam_launch.log  /tmp/nav2_launch.log"
echo -e " Presiona ${RED}Ctrl+C${NC} para guardar mapa + detener todo."
echo ""
echo -e " ${BOLD}Monitor de recursos (en otra terminal):${NC}"
echo -e "   ${CYAN}bash $TEST_DIR/recursos/monitor_sim.sh 120${NC}"
echo ""
echo -e "${GREEN}[4/4] Lanzando RViz en 15s (TF buffer settling)...${NC}"
sleep 15
ros2 run rviz2 rviz2 -d $CONFIG/main.rviz > /dev/null 2>&1 &
PID_RVIZ=$!
echo -e "${GREEN} ✓ RViz lanzado${NC}"
guardar_mapa_sim() {
    local NOMBRE="mapa_sim"
    local DESTINO="$WS/src/articubot_one/maps/map_sim"

    echo -e "\n${CYAN}══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW} Guardando mapa de simulación antes de cerrar...${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"

    set +u
    source "$WS/install/setup.bash" 2>/dev/null || true
    set -u

    python3 "$GUARDAR_MAPA_PY" \
        --destino   "$DESTINO"       \
        --nombre    "$NOMBRE"        \
        --modo      sim              \
        --bag       "$BAG_SLAM_DIR"  \
        --slam-pid  "${PID_SLAM}"    \
        --ws        "$WS"            \
    || echo -e "${RED} ✗ guardar_mapa.py terminó con error (ver mensajes arriba)${NC}"
}
trap "
set +e
guardar_mapa_sim
if [ -n '${PID_BAG}' ]; then
    kill '${PID_BAG}' 2>/dev/null || true
    wait '${PID_BAG}' 2>/dev/null || true
    echo -e '${GREEN} ✓ Rosbag detenido: ${BAG_SLAM_DIR}${NC}'
fi
rm -f /tmp/sim_ready /tmp/sim_nav2_ready
echo -e '\n${YELLOW}Deteniendo simulación...${NC}'
kill -- -\$PID_SLAM 2>/dev/null || kill \$PID_SLAM 2>/dev/null || true
sleep 2
kill -- -\$PID_SIM 2>/dev/null || kill \$PID_SIM 2>/dev/null || true
kill \$PID_NAV \$PID_RVIZ 2>/dev/null || true
killall -9 gzserver gzclient robot_state_publisher 2>/dev/null || true
killall -9 async_slam_toolbox_node 2>/dev/null || true
killall -9 controller_server planner_server bt_navigator 2>/dev/null || true
killall -9 recoveries_server waypoint_follower lifecycle_manager 2>/dev/null || true
killall -9 twist_mux joy_node teleop_node rviz2 2>/dev/null || true
ros2 daemon stop 2>/dev/null || true
echo -e '${GREEN}Listo.${NC}'
exit" SIGINT SIGTERM
echo -e " Monitoreando procesos (Ctrl+C para detener)..."
while true; do
    if ! kill -0 $PID_SIM 2>/dev/null; then
        echo -e "\n${YELLOW} gzserver terminó inesperadamente. Ejecutando cierre limpio...${NC}"
        if [ -n "${PID_BAG}" ]; then
            kill "${PID_BAG}" 2>/dev/null || true
            wait "${PID_BAG}" 2>/dev/null || true
        fi
        guardar_mapa_sim
        rm -f /tmp/sim_ready /tmp/sim_nav2_ready
        kill -- -$PID_SLAM 2>/dev/null || kill $PID_SLAM 2>/dev/null || true
        sleep 2
        kill $PID_NAV $PID_RVIZ 2>/dev/null || true
        killall -9 gzserver gzclient robot_state_publisher 2>/dev/null || true
        killall -9 async_slam_toolbox_node controller_server planner_server 2>/dev/null || true
        killall -9 bt_navigator recoveries_server waypoint_follower lifecycle_manager 2>/dev/null || true
        killall -9 twist_mux joy_node teleop_node rviz2 2>/dev/null || true
        ros2 daemon stop 2>/dev/null || true
        exit 0
    fi
    sleep 5
done