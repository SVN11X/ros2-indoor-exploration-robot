#!/bin/bash

WS=~/tesis_black_robot
CONFIG=$WS/src/articubot_one/config
TEST_DIR=$WS/experiments

export CYCLONEDDS_URI=file://$CONFIG/cyclonedds_pc.xml
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

set -uo pipefail   # OJO: sin -e para que un fallo en una iteración no aborte la sesión

GUARDAR_MAPA_PY="$TEST_DIR/utils/guardar_mapa.py"
ANALIZAR_SLAM_PY="$TEST_DIR/slam/analizar_slam.py"

[ ! -f "$ANALIZAR_SLAM_PY" ] && ANALIZAR_SLAM_PY=$(find "$TEST_DIR" -name "analizar_slam.py" 2>/dev/null | head -1)

RUN_EXPLORE_SH="$TEST_DIR/exploracion/run_explore.sh"
GENERAR_COMPARATIVA_PY="$TEST_DIR/utils/generar_comparativa.py"
[ ! -f "$GENERAR_COMPARATIVA_PY" ] && GENERAR_COMPARATIVA_PY=$(find "$TEST_DIR" -name "generar_comparativa.py" 2>/dev/null | head -1)

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

START_GLOBAL=$(date +%s)
SESION_TS="actual"
SESION_DIR="$TEST_DIR/sesiones_mapeo/sesion_actual"
# Sin versionamiento: se sobrescribe la sesión anterior.
rm -rf "$SESION_DIR"
mkdir -p "$SESION_DIR"

PID_JOY=""
PID_TWIST=""
PID_RVIZ=""
PID_SLAM=""
PID_NAV=""
PID_BAG=""
MONITOR_PID=""
SSH_PI=""
PI_IP=""
ITER_NUM=0
ITERACIONES_COMPLETADAS=()
FAILED_PROCESSES=()

elapsed_global() { echo $(( $(date +%s) - START_GLOBAL )); }

check_process() {
    local pid=$1
    local name=$2
    local log_file=$3
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
        echo -e "${RED} ✗ $name (PID: $pid) ha fallado${NC}"
        if [ -f "$log_file" ]; then
            echo -e "${YELLOW}   Últimas líneas del log:${NC}"
            tail -5 "$log_file" | sed 's/^/     /'
        fi
        FAILED_PROCESSES+=("$name")
        return 1
    fi
    return 0
}

monitor_processes() {
    while true; do
        sleep 5
        [ -n "${PID_JOY:-}" ] && ! kill -0 "$PID_JOY" 2>/dev/null && {
            echo -e "\n${RED}[FALLO] Joy node (PID: $PID_JOY) se detuvo${NC}"
        }
        [ -n "${PID_TWIST:-}" ] && ! kill -0 "$PID_TWIST" 2>/dev/null && {
            echo -e "\n${RED}[FALLO] Twist Mux (PID: $PID_TWIST) se detuvo${NC}"
        }
        [ -n "${PID_SLAM:-}" ] && ! kill -0 "$PID_SLAM" 2>/dev/null && {
            echo -e "\n${RED}[FALLO] SLAM Toolbox (PID: $PID_SLAM) se detuvo${NC}"
        }
        [ -n "${PID_NAV:-}" ] && ! kill -0 "$PID_NAV" 2>/dev/null && {
            echo -e "\n${RED}[FALLO] Nav2 (PID: $PID_NAV) se detuvo${NC}"
        }
    done
}

activate_nav2() {
    echo -e "${BLUE}   Intentando activar Nav2 manualmente...${NC}"
    sleep 2
    if ros2 service call /lifecycle_manager_navigation/activate \
        lifecycle_msgs/srv/ChangeState "{transition: {id: 3}}" 2>/dev/null; then
        echo -e "${GREEN}   ✓ Nav2 activado manualmente${NC}"
        return 0
    else
        echo -e "${YELLOW}   ⚠ No se pudo activar Nav2 manualmente${NC}"
        return 1
    fi
}

wait_for() {
    local desc="$1"; local timeout="$2"; shift 2
    local start=$(date +%s)
    local last_error=""
    local attempts=0
    while true; do
        local elapsed=$(( $(date +%s) - start ))
        local global=$(elapsed_global)
        attempts=$((attempts + 1))
        local output
        if output=$(timeout 20 bash -c "$*" 2>&1); then
            printf "\r${GREEN} ✓ %-45s [%3ds] (total: %ds)${NC}\n" "$desc" "$elapsed" "$global"
            return 0
        else
            last_error="$output"
            local exit_code=$?
        fi
        if [ $((elapsed % 10)) -eq 0 ] && [ $elapsed -gt 5 ]; then
            case "$desc" in
                *"Nav2 costmaps"*)
                    echo -e "\n${BLUE}[Diagnóstico] Nav2 no ha activado los costmaps${NC}"
                    activate_nav2
                    ;;
            esac
        fi
        if [ $elapsed -ge $timeout ]; then
            printf "\r${RED} ✗ %-45s [TIMEOUT %ds]${NC}\n" "$desc" "$timeout"
            [ -n "$last_error" ] && echo "$last_error" | head -3 | sed 's/^/     /'
            echo -e "${YELLOW}   Continuando de todos modos...${NC}"
            return 1
        fi
        if [ $((elapsed % 10)) -eq 0 ] && [ $elapsed -gt 0 ]; then
            printf "\r${YELLOW} ⏳ %-45s [%3ds / %ds] (intento %d)${NC}" \
                "$desc" "$elapsed" "$timeout" "$attempts"
        else
            printf "\r${YELLOW} ⏳ %-45s [%3ds / %ds]${NC}" "$desc" "$elapsed" "$timeout"
        fi
        sleep 2
    done
}

pre_setup() {
    export ROS_DOMAIN_ID=0
    unset ROS_LOCALHOST_ONLY

    echo ""
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN} Lanzamiento Mapeo Real — Sesión: ${SESION_TS}${NC}"
    echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
    echo -e "  Carpeta de sesión: ${SESION_DIR}"
    echo ""

    PI_IP="${ROBOT_PI_IP:-}"
    if [ -z "$PI_IP" ]; then
        echo -e "${YELLOW}IP de la Raspberry Pi (deja vacío para omitir SSH):${NC}"
        echo -n " > "
        read -r -t 20 PI_IP || PI_IP=""
    fi
    if [ -n "$PI_IP" ]; then
        SSH_PI="ubuntu@${PI_IP}"
        echo -e "${GREEN} ✓ Pi configurada: ${SSH_PI}${NC}"
    else
        echo -e "${YELLOW} Sin IP — se omite monitor_pi vía SSH${NC}"
    fi
    echo ""

    rm -f /tmp/mapeo_nav2_ready /tmp/mapeo_ready

    echo -e "${YELLOW}[PRE] Limpiando daemon ROS 2...${NC}"
    ros2 daemon stop 2>/dev/null && echo -e "${GREEN} ✓ Daemon detenido${NC}" \
        || echo -e "${YELLOW} ⚠ Daemon no estaba corriendo${NC}"
    sleep 3
    echo -e "${GREEN} ✓ Daemon reiniciado${NC}"

    echo -e "${YELLOW}[PRE] Verificando que el robot esté en línea...${NC}"
    if [ -n "$SSH_PI" ]; then
        if ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_PI" \
            "test -f /tmp/robot_ready" 2>/dev/null; then
            echo -e "${GREEN} ✓ /tmp/robot_ready encontrado en la Pi${NC}"
        else
            echo -e "${RED} ✗ /tmp/robot_ready no existe en la Pi${NC}"
            echo -e "${YELLOW}   Continuando de todos modos (verificando por DDS)...${NC}"
        fi
    fi

    wait_for "Robot publicando /odom" 30 \
        "ros2 topic list 2>/dev/null | grep -q '/odom'" || true
    wait_for "Robot publicando /scan" 60 \
        "ros2 topic info /scan 2>/dev/null | grep -qE 'Publisher count: [1-9]'" || true
    wait_for "TF odom→base_link disponible" 60 \
        "timeout 4 ros2 run tf2_ros tf2_echo odom base_link 2>&1 | grep -q 'Translation'" || true

    echo -e "${GREEN} ✓ Robot detectado en la red DDS${NC}"
    echo ""

    echo -e "${YELLOW}[0/N] Limpiando procesos anteriores en la PC...${NC}"
    rm -f /tmp/joystick_launch.log /tmp/twistmux_launch.log \
          /tmp/slam_launch.log /tmp/nav2_launch.log /tmp/bag_slam_real.log
    killall -9 joy_node teleop_node twist_mux 2>/dev/null || true
    killall -9 async_slam_toolbox_node 2>/dev/null || true
    killall -9 controller_server planner_server bt_navigator 2>/dev/null || true
    killall -9 recoveries_server waypoint_follower lifecycle_manager 2>/dev/null || true
    killall -9 explore_server 2>/dev/null || true
    pkill -f 'explore.launch.py' 2>/dev/null || true
    pkill -f 'navigation_launch.py' 2>/dev/null || true
    killall -9 rviz2 2>/dev/null || true
    echo -e "${GREEN} ✓ Limpieza completada${NC}"

    echo -e "${YELLOW}[0/N] Compilando workspace...${NC}"
    local BUILD_START=$(date +%s)
    cd $WS
    if colcon build --symlink-install --executor sequential 2>&1 \
        | tee /tmp/build_output.log | tail -3; then
        local BUILD_TIME=$(( $(date +%s) - BUILD_START ))
        echo -e "${GREEN} ✓ Build completado [${BUILD_TIME}s]${NC}"
    else
        echo -e "${RED} ✗ ERROR: Falló la compilación${NC}"
        grep -i "error" /tmp/build_output.log | tail -5 | sed 's/^/     /'
        exit 1
    fi
    set +u; source install/setup.bash; set -u
    echo ""
}

lanzar_base_persistente() {
    monitor_processes &
    MONITOR_PID=$!

    echo -e "${GREEN}[BASE] Lanzando Joystick + Twist Mux (persistentes)...${NC}"

    ros2 launch articubot_one joystick.launch.py > /tmp/joystick_launch.log 2>&1 &
    PID_JOY=$!
    wait_for "Joy node publicando /joy" 20 \
        "ros2 topic list 2>/dev/null | grep -q '/joy'" || true

    ros2 run twist_mux twist_mux \
        --ros-args --params-file $CONFIG/twist_mux.yaml \
        -r cmd_vel_out:=diff_cont/cmd_vel_unstamped > /tmp/twistmux_launch.log 2>&1 &
    PID_TWIST=$!
    wait_for "Twist Mux activo" 20 \
        "ros2 topic list 2>/dev/null | grep -q 'cmd_vel_unstamped'" || true

    wait_for "TF base_link→laser_frame" 30 \
        "timeout 3 ros2 run tf2_ros tf2_echo base_link laser_frame 2>&1 | grep -q 'Translation'" || true

    echo -e "${GREEN}[BASE] Lanzando RViz2...${NC}"
    ros2 run rviz2 rviz2 -d $CONFIG/main.rviz > /dev/null 2>&1 &
    PID_RVIZ=$!
    sleep 2
    echo -e "${GREEN} ✓ RViz lanzado (PID: $PID_RVIZ)${NC}"
    echo ""
}

preparar_dirs_iteracion() {
    local NN_PAD=$(printf "%02d" $ITER_NUM)
    ITER_TS="iter${NN_PAD}"
    ITER_DIR="${SESION_DIR}/iteracion_${NN_PAD}"
    ITER_MAPEO="${ITER_DIR}/mapeo"
    ITER_EXPLORE="${ITER_DIR}/exploracion"
    ITER_SISTEMA="${ITER_DIR}/sistema"
    BAG_DIR="${ITER_MAPEO}/rosbag"

    mkdir -p "$ITER_MAPEO" "$ITER_EXPLORE" "$ITER_SISTEMA"

    cp "$CONFIG/nav2_params.yaml" "${ITER_SISTEMA}/nav2_params.yaml" 2>/dev/null || true
    cp "$CONFIG/explore.yaml" "${ITER_SISTEMA}/explore.yaml" 2>/dev/null || true
    cp "$CONFIG/mapper_params_online_async.yaml" "${ITER_SISTEMA}/mapper_params.yaml" 2>/dev/null || true
}

lanzar_slam() {
    echo -e "${GREEN}[ITER ${ITER_NUM}] Lanzando SLAM Toolbox...${NC}"
    setsid ros2 launch articubot_one online_async_launch.py \
        params_file:=$CONFIG/mapper_params_online_async.yaml \
        use_sim_time:=false > /tmp/slam_launch.log 2>&1 &
    PID_SLAM=$!
    if ! wait_for "SLAM publicando /map" 45 \
        "ros2 topic list 2>/dev/null | grep -q '/map'"; then
        echo -e "${RED} ✗ SLAM Toolbox falló${NC}"
        check_process "$PID_SLAM" "SLAM Toolbox" "/tmp/slam_launch.log"
        return 1
    fi

    echo -e "${BLUE}[ITER ${ITER_NUM}] Esperando inicialización del mapa...${NC}"
    if ! wait_for "TF map→odom disponible" 90 \
        "timeout 15 ros2 run tf2_ros tf2_echo map odom 2>&1 | grep -q Translation"; then
        echo -e "${YELLOW}   SLAM continuará inicializando cuando el robot se mueva${NC}"
    fi
    return 0
}

lanzar_rosbag() {
    echo -e "${YELLOW}[ITER ${ITER_NUM}] Iniciando rosbag...${NC}"
    if ros2 bag record \
        /odom /scan /tf /tf_static /map \
        -o "$BAG_DIR" > /tmp/bag_slam_real.log 2>&1 &
    then
        PID_BAG=$!
        echo -e "${GREEN} ✓ Bag: ${BAG_DIR}${NC}"
    else
        echo -e "${RED} ✗ No se pudo iniciar rosbag${NC}"
        tail -5 /tmp/bag_slam_real.log | sed 's/^/     /'
    fi
}

lanzar_monitor_pi() {
    if [ -z "$SSH_PI" ]; then
        echo -e "${YELLOW}   (Monitor Pi omitido — sin SSH)${NC}"
        return 0
    fi
    local NN_PAD=$(printf "%02d" $ITER_NUM)
    local PI_TAG="iter${NN_PAD}"

    echo -e "${YELLOW}[ITER ${ITER_NUM}] Lanzando monitor_pi.sh en la Pi (tag=${PI_TAG})...${NC}"

    local PI_MONITOR_SCRIPT="~/robot_ws/test/recursos/monitor_pi.sh"

    if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_PI" \
        "test -f $PI_MONITOR_SCRIPT" 2>/dev/null; then
        echo -e "${RED} ✗ monitor_pi.sh no encontrado en la Pi en ${PI_MONITOR_SCRIPT}${NC}"
        echo -e "${YELLOW}   Continuando sin monitor de recursos${NC}"
        return 0
    fi

    if ssh "$SSH_PI" "nohup bash ${PI_MONITOR_SCRIPT} 5 999 ${PI_TAG} \
        > /tmp/monitor_pi_${PI_TAG}.log 2>&1 &
        echo \$! > /tmp/monitor_pi_${PI_TAG}.pid" 2>/tmp/ssh_error.log; then
        echo "$PI_TAG" > /tmp/last_monitor_tag
        echo -e "${GREEN} ✓ monitor_pi activo (tag: ${PI_TAG})${NC}"
    else
        echo -e "${RED} ✗ No se pudo lanzar monitor_pi.sh${NC}"
        [ -f /tmp/ssh_error.log ] && tail -3 /tmp/ssh_error.log | sed 's/^/     /'
    fi
}

lanzar_nav2() {
    echo -e "${GREEN}[ITER ${ITER_NUM}] Lanzando Nav2...${NC}"
    killall -9 controller_server planner_server bt_navigator 2>/dev/null || true
    killall -9 recoveries_server waypoint_follower lifecycle_manager 2>/dev/null || true
    pkill -f 'navigation_launch.py' 2>/dev/null || true
    sleep 2

    wait_for "TF odom→base_link antes de Nav2" 30         "timeout 4 ros2 run tf2_ros tf2_echo odom base_link 2>&1 | grep -q 'Translation'" || true
    wait_for "TF map→odom antes de Nav2" 30         "timeout 4 ros2 run tf2_ros tf2_echo map odom 2>&1 | grep -q 'Translation'" || true

    ros2 launch nav2_bringup navigation_launch.py         use_sim_time:=false         map_subscribe_transient_local:=true         params_file:=$CONFIG/nav2_params.yaml > /tmp/nav2_launch.log 2>&1 &
    PID_NAV=$!

    wait_for "Nav2 lifecycle manager disponible" 60         "ros2 service list 2>/dev/null | grep -q '/lifecycle_manager_navigation/is_active'" || true

    if ! wait_for "Nav2 costmaps activos" 60         "ros2 service list 2>&1 | grep -q '/global_costmap/clear_entirely_global_costmap'"; then
        activate_nav2
        sleep 5
        wait_for "Nav2 costmaps (post-activación)" 20             "ros2 service list 2>&1 | grep -q '/global_costmap/clear_entirely_global_costmap'" || true
    fi

    wait_for "Action /navigate_to_pose disponible" 45         "ros2 action list 2>&1 | grep -q '/navigate_to_pose'" || {
        echo -e "${YELLOW}   ⚠ navigate_to_pose no disponible — revisa /tmp/nav2_launch.log${NC}"
    }
    wait_for "Nav2 Managed nodes are active" 30         "grep -q 'Managed nodes are active' /tmp/nav2_launch.log" || {
        echo -e "${YELLOW}   ⚠ Nav2 no confirmó 'Managed nodes are active'. Último log:${NC}"
        tail -80 /tmp/nav2_launch.log | sed 's/^/     /'
    }

if ! kill -0 "$PID_NAV" 2>/dev/null; then
        echo -e "${RED} ✗ Nav2 murió antes de iniciar exploración.${NC}"
        tail -120 /tmp/nav2_launch.log | sed 's/^/     /'
        return 1
    fi
    echo -e "${YELLOW}[ITER ${ITER_NUM}] Calentando global_costmap (scan + static_layer)...${NC}"
    wait_for "Scan disponible para costmap" 20 \
        "timeout 5 ros2 topic echo /scan --once --field header.frame_id > /tmp/_scan_chk 2>/dev/null && [ -s /tmp/_scan_chk ]" || true
    wait_for "global_costmap poblado con celdas FREE" 30 \
        "timeout 5 ros2 topic echo /global_costmap/costmap --once --field data > /tmp/_cm_chk 2>/dev/null && grep -q -m1 -E '(^|[^0-9-])0([^0-9]|\$)' /tmp/_cm_chk" || \
        echo -e "${YELLOW}   ⚠ No se pudo confirmar contenido del costmap — explore puede fallar${NC}"
    sleep 3

    touch /tmp/mapeo_nav2_ready
    touch /tmp/mapeo_ready
}

ejecutar_exploracion() {
    if [ ! -f "$RUN_EXPLORE_SH" ]; then
        echo -e "${RED} ✗ No se encontró run_explore.sh en ${RUN_EXPLORE_SH}${NC}"
        return 1
    fi

    local NN_PAD=$(printf "%02d" $ITER_NUM)
    echo ""
    echo -e "${MAGENTA}══════════════════════════════════════════════════════${NC}"
    echo -e "${MAGENTA}  Invocando run_explore.sh — Iteración ${NN_PAD}${NC}"
    echo -e "${MAGENTA}══════════════════════════════════════════════════════${NC}"
    killall -9 explore_server 2>/dev/null || true
    pkill -f 'explore.launch.py' 2>/dev/null || true
    sleep 2

    echo -e "${CYAN}  Ctrl+I → interrumpir iteración y pasar a la siguiente${NC}"
    echo -e "${CYAN}  Ctrl+C → detener sesión completa${NC}"
    echo ""

    # Exploración en background (stdin cerrado para no competir con read)
    bash "$RUN_EXPLORE_SH" real 60 \
        --outdir "$ITER_EXPLORE" \
        --mapdir "$ITER_MAPEO" \
        --iter-label "$NN_PAD" \
        --no-prompt < /dev/null &
    local EXPLORE_PID=$!

    EXPLORE_INTERRUPTED=0

    # Poner terminal en modo raw para capturar Ctrl+I
    local OLD_STTY=$(stty -g)
    stty -icanon min 0 time 0 -echo

    # Foreground: esperar fin natural o Ctrl+I
    while kill -0 $EXPLORE_PID 2>/dev/null; do
        if read -t 1 -N 1 key 2>/dev/null; then
            if [[ "$key" == $'\t' ]]; then
                echo ""
                echo -e "${YELLOW}══════════════════════════════════════════════════════${NC}"
                echo -e "${YELLOW} ⚡ Ctrl+I — Cerrando exploración, pasando a siguiente${NC}"
                echo -e "${YELLOW}══════════════════════════════════════════════════════${NC}"
                EXPLORE_INTERRUPTED=1
                kill -- -$EXPLORE_PID 2>/dev/null || kill $EXPLORE_PID 2>/dev/null || true
                killall -9 explore_server 2>/dev/null || true
                pkill -f 'explore.launch.py' 2>/dev/null || true
                pkill -f 'run_explore.sh' 2>/dev/null || true
                break
            fi
        fi
    done

    # Restaurar terminal
    stty "$OLD_STTY"

    wait $EXPLORE_PID 2>/dev/null || true
    local EXPLORE_EXIT=$?

    if [ $EXPLORE_INTERRUPTED -eq 1 ]; then
        echo -e "${YELLOW} ⚠ Exploración interrumpida por Ctrl+I${NC}"
    elif [ $EXPLORE_EXIT -ne 0 ]; then
        echo -e "${YELLOW} ⚠ run_explore.sh terminó con código ${EXPLORE_EXIT}${NC}"
    fi
    return 0
}

cerrar_rosbag() {
    if [ -z "${PID_BAG}" ]; then return 0; fi
    echo -e "${YELLOW}[POST] Cerrando rosbag...${NC}"
    kill -INT "${PID_BAG}" 2>/dev/null || true
    local wait_count=0
    while kill -0 "${PID_BAG}" 2>/dev/null && [ $wait_count -lt 15 ]; do
        sleep 1
        wait_count=$((wait_count + 1))
    done
    PID_BAG=""
    echo -e "${GREEN} ✓ Rosbag cerrado${NC}"
}

capturar_tf_tree() {
    echo -e "${YELLOW}[POST] Capturando árbol TF...${NC}"
    (
        cd "$ITER_SISTEMA"
        timeout 8 ros2 run tf2_tools view_frames > /dev/null 2>&1 || true
        local FRAMES_PDF=$(ls -t frames*.pdf 2>/dev/null | head -1)
        if [ -n "$FRAMES_PDF" ]; then
            mv "$FRAMES_PDF" "tf_tree.pdf"
            if command -v pdftoppm &>/dev/null; then
                pdftoppm "tf_tree.pdf" "tf_tree" -png -r 200 2>/dev/null || true
                [ -f "tf_tree-1.png" ] && mv "tf_tree-1.png" "tf_tree.png"
            fi
            echo -e "${GREEN} ✓ TF tree → ${ITER_SISTEMA}/tf_tree.{pdf,png}${NC}"
        fi
        rm -f frames*.gv frames*.dot 2>/dev/null || true
    )
}

copiar_monitor_pi_csv() {
    if [ -z "$SSH_PI" ] || [ ! -f /tmp/last_monitor_tag ]; then
        return 0
    fi
    local TAG=$(cat /tmp/last_monitor_tag)
    echo -e "${YELLOW}[POST] Deteniendo monitor_pi en la Pi (tag=${TAG})...${NC}"

    ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_PI" \
        "kill -INT \$(cat /tmp/monitor_pi_${TAG}.pid 2>/dev/null) 2>/dev/null || true" 2>/dev/null || true

    sleep 3

    local REMOTE_BASE=""
    for CANDIDATE in \
        "~/robot_ws/test/recursos/monitor_pi" \
        "~/tesis_black_robot/test/recursos/monitor_pi"
    do
        if ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_PI" \
            "test -d $CANDIDATE" 2>/dev/null; then
            REMOTE_BASE="$CANDIDATE"
            break
        fi
    done

    if [ -z "$REMOTE_BASE" ]; then
        echo -e "${YELLOW}   ⚠ No se encontró el directorio monitor_pi en la Pi${NC}"
        echo -e "${YELLOW}     Verifica con: ssh ${SSH_PI} 'find ~ -name monitor_pi_${TAG}*.csv'${NC}"
        return 0
    fi

    local REMOTE_DIR=$(ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_PI" \
        "test -d ${REMOTE_BASE}/monitor_pi/${TAG} && echo ${REMOTE_BASE}/monitor_pi/${TAG}/" 2>/dev/null | tr -d '\r\n')

    if [ -z "$REMOTE_DIR" ]; then
        echo -e "${YELLOW}   ⚠ No se encontró carpeta de output para tag=${TAG}${NC}"
        echo -e "${YELLOW}     Buscar manualmente: ssh ${SSH_PI} ls ${REMOTE_BASE}/${NC}"
        return 0
    fi

    if timeout 15 scp -r -o ConnectTimeout=5 \
        "ubuntu@${PI_IP}:${REMOTE_DIR}*" \
        "${ITER_SISTEMA}/" 2>/dev/null; then
        local COPIED=$(find "${ITER_SISTEMA}" -maxdepth 1 -type f \( -name 'monitor_pi*.csv' -o -name 'monitor_pi*.tex' \) 2>/dev/null | wc -l)
        echo -e "${GREEN} ✓ ${COPIED} archivo(s) de monitor_pi copiados desde ${REMOTE_DIR}${NC}"
        find "${ITER_SISTEMA}" -maxdepth 1 -type f \( -name 'monitor_pi*.csv' -o -name 'monitor_pi*.tex' \) 2>/dev/null | sed 's/^/     /'
    else
        echo -e "${YELLOW}   ⚠ Falló el scp desde ${REMOTE_DIR}${NC}"
        echo -e "${YELLOW}     Verifica conectividad SSH${NC}"
    fi
    rm -f /tmp/last_monitor_tag
}

ejecutar_analizar_slam() {
    if [ ! -f "$ANALIZAR_SLAM_PY" ]; then
        echo -e "${YELLOW}[POST] analizar_slam.py no encontrado — omitiendo${NC}"
        return 0
    fi

    local PGM=$(ls "${ITER_MAPEO}"/mapa_explore_real_*.pgm 2>/dev/null | head -1)
    if [ -z "$PGM" ] || [ ! -f "$PGM" ]; then
        echo -e "${YELLOW}[POST] No se encontró mapa .pgm — omitiendo analizar_slam.py${NC}"
        return 0
    fi

    echo -e "${YELLOW}[POST] Ejecutando analizar_slam.py...${NC}"
    set +e
    set +u
    source "$WS/install/setup.bash" 2>/dev/null || true
    python3 "$ANALIZAR_SLAM_PY" \
        --modo real \
        --bag "$BAG_DIR" \
        --pgm "$PGM" \
        --out "$ITER_MAPEO" \
        --suffix "real" \
        2>&1 | tee "${ITER_MAPEO}/analizar_slam.log"
    local SLAM_EXIT=$?
    set -u
    if [ $SLAM_EXIT -eq 0 ]; then
        echo -e "${GREEN} ✓ Análisis SLAM completado${NC}"
    else
        echo -e "${YELLOW} ⚠ analizar_slam.py terminó con código $SLAM_EXIT${NC}"
    fi
}

generar_resumen_iteracion() {
    local NN_PAD=$(printf "%02d" $ITER_NUM)
    local RESUMEN="${ITER_DIR}/RESUMEN_iteracion_${NN_PAD}.txt"
    {
        echo "════════════════════════════════════════════════════════════"
        echo "  ITERACIÓN ${NN_PAD} — Sesión ${SESION_TS}"
        echo "════════════════════════════════════════════════════════════"
        echo ""
        echo "Timestamp:     ${ITER_TS}"
        echo "Fecha:         $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
        echo "── ARCHIVOS GENERADOS ──────────────────────────────────────"
        echo ""
        echo "Mapeo (${ITER_MAPEO}):"
        ls -la "${ITER_MAPEO}/" 2>/dev/null | grep -v '^total\|^d' | awk '{print "  " $NF}' | grep -v '^\.$\|^\.\.$' | head -20
        echo ""
        echo "Exploración (${ITER_EXPLORE}):"
        ls -la "${ITER_EXPLORE}/" 2>/dev/null | grep -v '^total\|^d' | awk '{print "  " $NF}' | grep -v '^\.$\|^\.\.$' | head -20
        echo ""
        echo "Sistema (${ITER_SISTEMA}):"
        ls -la "${ITER_SISTEMA}/" 2>/dev/null | grep -v '^total\|^d' | awk '{print "  " $NF}' | grep -v '^\.$\|^\.\.$' | head -20
        echo ""
        echo "── MÉTRICAS DE EXPLORACIÓN ─────────────────────────────────"
        local EXPLORE_CSV=$(ls "${ITER_EXPLORE}"/explore_metricas_*.csv 2>/dev/null | head -1)
        if [ -f "$EXPLORE_CSV" ]; then
            cat "$EXPLORE_CSV"
        else
            echo "  (no disponible)"
        fi
        echo ""
        echo "── MÉTRICAS SLAM ───────────────────────────────────────────"
        local SLAM_CSV=$(ls "${ITER_MAPEO}"/slam_metricas_*.csv 2>/dev/null | head -1)
        if [ -f "$SLAM_CSV" ]; then
            cat "$SLAM_CSV"
        else
            echo "  (no disponible)"
        fi
    } > "$RESUMEN"
    echo -e "${GREEN} ✓ Resumen iteración: ${RESUMEN}${NC}"
}

reset_para_siguiente_iteracion() {
    echo -e "${YELLOW}══════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  Limpiando para siguiente iteración (RESET COMPLETO)${NC}"
    echo -e "${YELLOW}══════════════════════════════════════════════════════${NC}"

    if [ -n "${PID_SLAM}" ]; then
        kill -- -${PID_SLAM} 2>/dev/null || kill ${PID_SLAM} 2>/dev/null || true
    fi
    killall -9 async_slam_toolbox_node 2>/dev/null || true
    PID_SLAM=""

    if [ -n "${PID_NAV}" ]; then
        kill ${PID_NAV} 2>/dev/null || true
    fi
    killall -9 controller_server planner_server bt_navigator 2>/dev/null || true
    killall -9 recoveries_server waypoint_follower lifecycle_manager 2>/dev/null || true
    PID_NAV=""

    killall -9 explore_server 2>/dev/null || true
    pkill -f 'explore.launch.py' 2>/dev/null || true
    pkill -9 -f 'run_explore.sh' 2>/dev/null || true
    pkill -f 'navigation_launch.py' 2>/dev/null || true

    rm -f /tmp/mapeo_nav2_ready /tmp/mapeo_ready

    echo -e "${GREEN} ✓ Reset completo — Joystick/Twist/RViz siguen activos${NC}"
    sleep 3
}

generar_comparativa_sesion() {
    if [ ${#ITERACIONES_COMPLETADAS[@]} -eq 0 ]; then
        echo -e "${YELLOW}[FINAL] No hay iteraciones completas — sin comparativa${NC}"
        return 0
    fi

    if [ ! -f "$GENERAR_COMPARATIVA_PY" ]; then
        echo -e "${YELLOW}[FINAL] generar_comparativa.py no encontrado — omitiendo${NC}"
        echo -e "${YELLOW}   Búscalo en: $TEST_DIR/utils/${NC}"
        return 0
    fi

    echo -e "${YELLOW}[FINAL] Generando comparativa de iteraciones...${NC}"
    set +e
    python3 "$GENERAR_COMPARATIVA_PY" \
        --sesion-dir "$SESION_DIR" \
        2>&1 | tee "${SESION_DIR}/comparativa.log"
    set -e
}

generar_resumen_sesion() {
    local RESUMEN="${SESION_DIR}/RESUMEN_SESION_completo.txt"
    {
        echo "════════════════════════════════════════════════════════════"
        echo "  SESIÓN COMPLETA DE MAPEO — ${SESION_TS}"
        echo "════════════════════════════════════════════════════════════"
        echo ""
        echo "Inicio:        $(date -d @${START_GLOBAL} '+%Y-%m-%d %H:%M:%S')"
        echo "Fin:           $(date '+%Y-%m-%d %H:%M:%S')"
        echo "Duración:      $(( $(date +%s) - START_GLOBAL )) segundos"
        echo ""
        echo "Iteraciones completadas: ${#ITERACIONES_COMPLETADAS[@]}"
        echo ""
        echo "── ITERACIONES ─────────────────────────────────────────────"
        for iter in "${ITERACIONES_COMPLETADAS[@]}"; do
            echo "  $iter"
        done
        echo ""
        echo "── ARCHIVOS DE NIVEL SESIÓN ────────────────────────────────"
        ls "${SESION_DIR}/" | grep -v "^iteracion_" | sed 's/^/  /'
        echo ""
        echo "── ESTRUCTURA DE ARCHIVOS ──────────────────────────────────"
        echo ""
        echo "Cada iteración contiene:"
        echo "  mapeo/         (mapa.pgm, slam_trayectoria.png, slam_metricas.csv, ...)"
        echo "  exploracion/   (explore_metricas.csv, explore_tabla.tex, odom_trayectoria.csv)"
        echo "  sistema/       (tf_tree.png, monitor_pi.csv, snapshots de configs)"
        echo ""
        echo "Para tu tesis, consulta:"
        echo "  ${SESION_DIR}/comparativa_iteraciones.tex"
        echo "  ${SESION_DIR}/comparativa_iteraciones.csv"
    } > "$RESUMEN"
    echo -e "${GREEN} ✓ Resumen de sesión: ${RESUMEN}${NC}"
}

cleanup_total() {
    echo -e "${YELLOW}[FINAL] Cleanup total — deteniendo todos los procesos${NC}"
    kill $MONITOR_PID 2>/dev/null || true

    if [ -n "${SSH_PI}" ]; then
        ssh -o ConnectTimeout=5 -o BatchMode=yes "$SSH_PI" \
            'pkill -f monitor_pi.sh 2>/dev/null || true' 2>/dev/null || true
    fi

    [ -n "$PID_SLAM" ] && (kill -- -${PID_SLAM} 2>/dev/null || kill ${PID_SLAM} 2>/dev/null) || true
    [ -n "$PID_NAV" ]  && kill ${PID_NAV} 2>/dev/null || true
    [ -n "$PID_JOY" ]  && kill ${PID_JOY} 2>/dev/null || true
    [ -n "$PID_TWIST" ] && kill ${PID_TWIST} 2>/dev/null || true
    [ -n "$PID_RVIZ" ] && kill ${PID_RVIZ} 2>/dev/null || true
    [ -n "$PID_BAG" ]  && kill -INT ${PID_BAG} 2>/dev/null || true  # ← rosbag

    killall -9 joy_node teleop_node twist_mux 2>/dev/null || true
    killall -9 async_slam_toolbox_node 2>/dev/null || true
    killall -9 controller_server planner_server bt_navigator 2>/dev/null || true
    killall -9 recoveries_server waypoint_follower lifecycle_manager 2>/dev/null || true
    killall -9 explore_server 2>/dev/null || true
    killall -9 rviz2 2>/dev/null || true
    killall -9 robot_state_publisher 2>/dev/null || true
    pkill -9 -f 'run_explore.sh' 2>/dev/null || true
    pkill -f 'explore.launch.py' 2>/dev/null || true      # ← launch de explore
    pkill -f 'navigation_launch.py' 2>/dev/null || true    # ← launch de nav2

    ros2 daemon stop 2>/dev/null
    echo -e "${GREEN}PC detenida.${NC}"
}

trap '
    echo -e "\n${RED}══════════════════════════════════════════════════════${NC}"
    echo -e "${RED} INTERRUPCIÓN EXTERNA — Cleanup de emergencia${NC}"
    echo -e "${RED}══════════════════════════════════════════════════════${NC}"
    cleanup_total
    exit 130
' SIGINT SIGTERM

pre_setup
lanzar_base_persistente

while true; do
    ITER_NUM=$((ITER_NUM + 1))
    NN_PAD=$(printf "%02d" $ITER_NUM)

    echo ""
    echo -e "${BLUE}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║         ITERACIÓN ${NN_PAD}                           ║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════╝${NC}"

    preparar_dirs_iteracion
    echo -e "  Carpeta: ${ITER_DIR}"
    echo ""

    lanzar_slam || {
        echo -e "${RED} ✗ Falló SLAM en iteración ${NN_PAD} — abortando iteración${NC}"
        ITER_NUM=$((ITER_NUM - 1))  # No contar esta iteración fallida
        reset_para_siguiente_iteracion
        continue
    }

    lanzar_rosbag
    lanzar_monitor_pi
    lanzar_nav2

    if [ ${#FAILED_PROCESSES[@]} -gt 0 ]; then
        echo -e "${YELLOW} ⚠ Procesos fallidos: ${FAILED_PROCESSES[*]}${NC}"
        FAILED_PROCESSES=()
    fi

    echo ""
    echo -e "${YELLOW}[5/5] ¿Lanzar exploración autónoma de fronteras? [s/N]: ${NC}"
    read -r RESP_EXPLORE
    if [[ "$RESP_EXPLORE" =~ ^[sS]$ ]]; then

        ejecutar_exploracion
    else
        echo -e "${YELLOW} Iteración sin exploración autónoma — solo SLAM manual${NC}"
        echo -e "${CYAN} Mueve el robot con el joystick para construir mapa. Presiona ENTER cuando termines.${NC}"
        read -r
    fi

    cerrar_rosbag
    capturar_tf_tree
    copiar_monitor_pi_csv
    ejecutar_analizar_slam
    generar_resumen_iteracion

    ITERACIONES_COMPLETADAS+=("iteracion_${NN_PAD}")

    echo ""
    echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN} ✓ Iteración ${NN_PAD} completada${NC}"
    echo -e "${GREEN}   Resultados en: ${ITER_DIR}${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"

    echo ""
    echo -e "${MAGENTA}¿Iniciar siguiente iteración? [s/N]: ${NC}"
    read -r RESP_NEXT
    if [[ "$RESP_NEXT" =~ ^[sS]$ ]]; then
        reset_para_siguiente_iteracion
        continue
    else
        echo -e "${CYAN} Finalizando sesión...${NC}"
        break
    fi
done

echo ""
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"
echo -e "${CYAN} CIERRE DE SESIÓN — Generando comparativa y cleanup${NC}"
echo -e "${CYAN}══════════════════════════════════════════════════════${NC}"

generar_comparativa_sesion
generar_resumen_sesion
cleanup_total

TOTAL_TIME=$(elapsed_global)
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN} ✓ SESIÓN COMPLETADA${NC}"
echo -e "${GREEN}   Tiempo total: ${TOTAL_TIME} segundos${NC}"
echo -e "${GREEN}   Iteraciones:  ${#ITERACIONES_COMPLETADAS[@]}${NC}"
echo -e "${GREEN}   Carpeta:      ${SESION_DIR}${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════${NC}"
echo ""
echo -e " ${BOLD}Para tu tesis:${NC}"
echo -e "   ${CYAN}${SESION_DIR}/comparativa_iteraciones.tex${NC}"
echo -e "   ${CYAN}${SESION_DIR}/RESUMEN_SESION_completo.txt${NC}"
echo ""

exit 0