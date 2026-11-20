#!/bin/bash

WS=~/robot_ws
TEST_DIR=$WS/experiments
CONFIG=$WS/src/articubot_one/config

export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
set -u

echo "[PRE] Sincronizando reloj..."
sudo chronyc makestep 2>/dev/null || true
sleep 2
echo " ✓ Reloj sincronizado"

set -o pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

START_GLOBAL=$(date +%s)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PID_ROBOT=""
PID_LIDAR=""

elapsed_global() { echo $(( $(date +%s) - START_GLOBAL )); }
wait_for() {
    local desc="$1"; local tout="$2"; local check_cmd="$3"
    local diag_cmd="${4:-}"
    local start=$(date +%s)
    while true; do
        local elapsed=$(( $(date +%s) - start ))
        local global=$(elapsed_global)
        if timeout 15 bash -c "$check_cmd" > /dev/null 2>&1; then
            printf "\r${GREEN} ✓ %-45s [%3ds] (total: %ds)${NC}\n" "$desc" "$elapsed" "$global"
            return 0
        fi
        if [ $elapsed -ge $tout ]; then
            printf "\r${RED} ✗ %-45s [TIMEOUT %ds]${NC}\n" "$desc" "$tout"
            if [ -n "$diag_cmd" ]; then
                echo -e "${YELLOW}   ┌─ Diagnóstico:${NC}"
                eval "$diag_cmd" 2>&1 | head -30 | sed 's/^/   │ /'
                echo -e "${YELLOW}   └─────────────${NC}"
            fi
            echo -e "${YELLOW}   Continuando de todos modos...${NC}"
            return 1
        fi
        printf "\r${YELLOW} ⏳ %-45s [%3ds / %ds]${NC}" "$desc" "$elapsed" "$tout"
        sleep 2
    done
}
diag_lidar() {
    if pgrep -f "rplidar_serial_publisher.py" > /dev/null 2>&1; then
        echo "CAPA 1 [proceso] ............. ✓ vivo (PID $(pgrep -f rplidar_serial_publisher.py | head -1))"
        local L1_OK=1
    else
        echo "CAPA 1 [proceso] ............. ✗ MUERTO"
        echo "  → Acción: revisar /tmp/rplidar_launch.log para errores de carga"
        local L1_OK=0
    fi
    if grep -qE "Scan iniciado|Scan started|Sincronizado al inicio" /tmp/rplidar_launch.log 2>/dev/null; then
        echo "CAPA 2 [init lidar] ........... ✓ completo (scan iniciado)"
        local L2_OK=1
    else
        echo "CAPA 2 [init firmware] ....... ✗ INCOMPLETO"
        echo "  → DIAGNÓSTICO: el driver no logró handshake con el firmware del lidar."
        echo "  → Causa típica: estado degenerado del A1 por kill brusco previo."
        echo "  → Acción: sudo reboot en la Pi (corta 5V del lidar y resetea firmware)."
        local L2_OK=0
    fi
    local pub_count
    pub_count=$(ros2 topic info /scan 2>/dev/null | grep -oP 'Publisher count: \K[0-9]+' || echo "?")
    if [[ "$pub_count" =~ ^[1-9] ]]; then
        echo "CAPA 3 [publisher DDS] ....... ✓ registrado (Publisher count: $pub_count)"
    else
        echo "CAPA 3 [publisher DDS] ....... ✗ NO REGISTRADO (Publisher count: $pub_count)"
        if [ "$L1_OK" = "1" ] && [ "$L2_OK" = "1" ]; then
            echo "  → DIAGNÓSTICO: init OK pero el driver no publicó en el grafo."
            echo "  → Causa probable: ros2 daemon caído o config DDS inválida."
            echo "  → Acción: verificar FASTRTPS_DEFAULT_PROFILES_FILE y fastdds_unicast.xml."
        fi
    fi

    echo ""
    echo "── Últimas 10 líneas de rplidar_launch.log ──"
    tail -10 /tmp/rplidar_launch.log 2>&1
    echo ""
    echo "── Hardware (/dev/rlidar_gpio) ──"
    ls -la /dev/rlidar_gpio 2>&1
}

echo -e "\n${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN} Lanzamiento Robot Real — Raspberry Pi (v2.5)${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}\n"
echo -e "${YELLOW}[0/3] Limpiando procesos previos...${NC}"
rm -f /tmp/robot_ready /tmp/robot_launch.pid > /dev/null 2>&1 || true

PROCS="robot_state_publisher twist_mux joy_node teleop_node \
       async_slam_toolbox_node diff_drive_controller \
       joint_state_broadcaster rplidar_node rplidarNode \
       rplidar_composition scan_filter rplidar_serial_publisher"
for p in $PROCS; do
    pkill -9 -f "$p" > /dev/null 2>&1 || true
done

ros2 daemon stop > /dev/null 2>&1 || true
sleep 2
echo -e "${GREEN} ✓ Entorno limpio${NC}"
echo -e "${YELLOW}[0/3] Verificando Workspace...${NC}"
if [ ! -d "$WS" ]; then
    echo -e "${RED} ERROR: No existe el directorio $WS${NC}"
    exit 1
fi

cd "$WS"

colcon build --symlink-install --executor sequential \
    --packages-ignore explore_lite \
    2>&1 | tail -n 5 \
    || echo -e "${YELLOW} ! Aviso en el build${NC}"

if [ -f "install/setup.bash" ]; then
    set +u
    source install/setup.bash
    set -u
    echo -e "${GREEN} ✓ Workspace cargado correctamente${NC}"
else
    echo -e "${RED} ERROR CRÍTICO: No se encontró install/setup.bash${NC}"
    exit 1
fi
echo ""
cleanup_robot() {
    echo -e "\n${YELLOW}Deteniendo robot (Pi)...${NC}"
    [ -n "$PID_LIDAR" ] && kill -INT $PID_LIDAR 2>/dev/null || true
    [ -n "$PID_ROBOT" ] && kill -INT $PID_ROBOT 2>/dev/null || true
    sleep 3
    pkill -9 -f "launch_robot.launch.py"  2>/dev/null || true
    pkill -9 -f "rplidar.launch.py"       2>/dev/null || true
    pkill -9 robot_state_publisher        2>/dev/null || true
    pkill -9 diff_drive_controller        2>/dev/null || true
    pkill -9 joint_state_broadcaster      2>/dev/null || true
    pkill -9 rplidar_node                 2>/dev/null || true
    pkill -9 rplidarNode                  2>/dev/null || true
    pkill -9 rplidar_composition          2>/dev/null || true
    pkill -9 controller_manager           2>/dev/null || true

    timeout 5 ros2 daemon stop 2>/dev/null || true &

    rm -f /tmp/robot_ready
    echo -e "${GREEN}Pi detenida.${NC}"
    exit
}
trap 'cleanup_robot' SIGINT SIGTERM
echo -e "${GREEN}[1/3] Iniciando Robot Base...${NC}"

stty -F /dev/motor_controller -hupcl 2>/dev/null || true
sleep 0.5
ros2 launch articubot_one launch_robot.launch.py > /tmp/robot_launch.log 2>&1 &
PID_ROBOT=$!
wait_for "TF odom→base_link (implica /odom activo)" 150 \
    "timeout 5 ros2 run tf2_ros tf2_echo odom base_link 2>&1 | grep -q 'Translation'" \
    "echo '-- Últimas 10 líneas de robot_launch.log:'; tail -10 /tmp/robot_launch.log; echo '-- Proceso launch vivo?'; kill -0 $! 2>/dev/null && echo 'Sí (PID $!)' || echo 'NO — murió'; echo '-- /dev/motor_controller:'; ls -la /dev/motor_controller 2>&1; echo '-- Controladores:'; ros2 control list_controllers 2>/dev/null || echo '(controller_manager no responde)'"
if ! wait_for "Controlador diff_cont activo" 30 \
    "ros2 control list_controllers 2>/dev/null | grep -q 'diff_cont.*active'" \
    "echo '-- Controladores registrados:'; ros2 control list_controllers 2>/dev/null || echo '(no responde)'; echo '-- Últimas 5 líneas log:'; tail -5 /tmp/robot_launch.log"; then

    if ros2 control list_controllers 2>/dev/null | grep -q 'joint_broad.*active'; then
        echo -e "${YELLOW}   → joint_broad activo pero diff_cont no. Reintentando spawn manual...${NC}"
        if ros2 run controller_manager spawner.py diff_cont 2>&1 | tail -3; then
            sleep 2
            if ros2 control list_controllers 2>/dev/null | grep -q 'diff_cont.*active'; then
                echo -e "${GREEN}   ✓ diff_cont activado vía spawn manual${NC}"
            else
                echo -e "${RED}   ✗ Spawn manual también falló; revisar /tmp/robot_launch.log${NC}"
            fi
        fi
    fi
fi
echo ""
echo -e "${GREEN}[2/3] Iniciando RPLidar...${NC}"
ros2 launch articubot_one rplidar.launch.py > /tmp/rplidar_launch.log 2>&1 &
PID_LIDAR=$!
export -f diag_lidar
wait_for "RPLidar listo (proceso + init + publisher)" 60 \
    "pgrep -f rplidar_serial_publisher.py > /dev/null && grep -qE 'Scan iniciado|Scan started|Sincronizado al inicio' /tmp/rplidar_launch.log && ros2 topic info /scan | grep -qE 'Publisher count: [1-9]'" \
    "diag_lidar"
echo -e "${YELLOW}   Verificación opcional de flujo (puede tardar 30+s por DDS)...${NC}"
if ros2 topic info /scan 2>/dev/null | grep -qE 'Publisher count: [1-9]'; then
    sub_count=$(ros2 topic info /scan 2>/dev/null | grep -oP 'Subscription count: \K[0-9]+' | head -1)
    echo -e "${GREEN}   ✓ /scan publisher registrado (subs activos: ${sub_count:-0})${NC}"
else
    echo -e "${YELLOW}   ⚠ /scan publisher no detectado en el daemon${NC}"
    echo -e "${YELLOW}     (probablemente el daemon necesita más tiempo de discovery)${NC}"
fi
wait_for "TF base_link→laser_frame disponible" 60 \
    "timeout 5 ros2 run tf2_ros tf2_echo base_link laser_frame 2>&1 | grep -q 'Translation'" \
    "echo '-- tf2_echo base_link laser_frame:'; timeout 3 ros2 run tf2_ros tf2_echo base_link laser_frame 2>&1 | tail -5; echo '-- Frames en tf_static:'; timeout 3 ros2 topic echo /tf_static --qos-reliability reliable --qos-durability transient_local --once 2>&1 | grep -A1 child_frame_id | head -10 || echo '(sin datos)'"
echo ""
echo "$TIMESTAMP" > /tmp/robot_ready

TOTAL_TIME=$(elapsed_global)
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN} ✓ ROBOT LISTO PARA OPERAR — Raspberry Pi${NC}"
echo -e "${GREEN}   Tiempo total de arranque: ${TOTAL_TIME} segundos${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo ""
echo -e " ${BOLD}Tests habilitados ahora (modo REAL):${NC}"
echo -e "  test/linea_recta/run_prueba_recta.sh        ${GREEN}← /odom ✓${NC}"
echo -e "  test/prueba_giro/run_prueba_giro.sh         ${GREEN}← /odom ✓${NC}"
echo -e "  test/verificacion_tf/run_verificacion_tf.sh ${GREEN}← /tf ✓${NC}"
echo -e "  test/recursos/monitor_pi.sh                 ${GREEN}← /scan ✓ (correr aquí en Pi)${NC}"
echo -e "  test/navegacion/run_prueba_nav.sh           ${YELLOW}← requiere launch_mapeo_all.sh (PC)${NC}"
echo -e "  test/exploracion/run_explore.sh             ${YELLOW}← requiere launch_mapeo_all.sh (PC)${NC}"
echo -e "  test/slam/analizar_slam.py                  ${YELLOW}← post-proceso, lee bag de mapeo${NC}"
echo ""
echo -e " Para mapeo y navegación, en la PC ejecuta:"
echo -e "   ${CYAN}bash ~/tesis_black_robot/scripts/launch/launch_mapeo_all.sh${NC}"
echo ""
echo -e " Logs:"
echo -e "   /tmp/robot_launch.log   /tmp/rplidar_launch.log"
echo -e " Presiona ${RED}Ctrl+C${NC} para detener todo (envía SIGINT al lidar primero)."

wait