#!/usr/bin/env bash
# ============================================================
# run_prueba_recta.sh — Orquestador de la prueba de odometría
#   en trayectoria rectilínea (5 repeticiones, 2 m, 0.13 m/s)
#
# USO (desde la PC, con el robot ya encendido vía SSH):
#   bash ~/tesis_black_robot/experiments/linea_recta/run_prueba_recta.sh
# ============================================================
set -euo pipefail

export ROS_DOMAIN_ID=0
unset ROS_LOCALHOST_ONLY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_FILE="${SCRIPT_DIR}/distancias_reales.txt"
N_PRUEBAS=5

# ── fuentes ROS2 ─────────────────────────────────────────────────────────────
set +u
source /opt/ros/foxy/setup.bash
source "${SCRIPT_DIR}/../../install/setup.bash"       2>/dev/null || \
source "${HOME}/tesis_black_robot/install/setup.bash" 2>/dev/null || \
source "${HOME}/dev_ws/install/setup.bash"            2>/dev/null || \
{ echo "ERROR: no se encontró install/setup.bash — ajusta la ruta."; exit 1; }
set -u

# ── verificar que el robot esté lanzado ──────────────────────────────────────
echo ""
echo "============================================================"
echo "  PRE-REQUISITO: Robot activo en la Raspberry Pi"
echo "============================================================"
echo "  ¿Ya lanzaste la pila base del robot en la Pi?"
echo ""
echo "    [1] Sí, usé:  bash ~/robot_ws/launch_robot_all.sh"
echo "    [2] Sí, usé el modo manual (mapeo_robot.txt)"
echo "    [3] No — salir para lanzarlo primero"
echo ""
read -rp "  Selecciona una opción [1/2/3]: " ROBOT_OPT

case "${ROBOT_OPT}" in
    1)
        echo "  ✓ Modo automático confirmado."
        ;;
    2)
        echo "  ✓ Modo manual confirmado."
        echo "  Recuerda que deben estar activos:"
        echo "    - ros2 launch articubot_one launch_robot.launch.py"
        echo "    - ros2 launch articubot_one rplidar.launch.py"
        read -rp "  ¿Ambos están corriendo? Presiona ENTER para continuar..."
        ;;
    3|*)
        echo ""
        echo "  Lanza primero el robot en la Pi:"
        echo "    ssh ubuntu@<IP_ROBOT>"
        echo "    bash ~/robot_ws/launch_robot_all.sh"
        echo ""
        echo "  O en modo manual (ver mapeo_robot.txt)."
        exit 0
        ;;
esac

# ── verificar que /odom se está publicando ────────────────────────────────────
echo ""
echo "=== Verificando /odom ==="
ros2 daemon stop > /dev/null 2>&1; sleep 5
ros2 daemon start > /dev/null 2>&1; sleep 3

ODOM_FOUND=false
for INTENTO in 1 2 3 4 5; do
    echo "  Intento ${INTENTO}/5..."
    if timeout 8 ros2 topic list 2>/dev/null | grep -q "/odom"; then
        ODOM_FOUND=true
        break
    fi
    sleep 3
done

if [ "${ODOM_FOUND}" = false ]; then
    echo "ERROR: /odom no disponible tras 5 intentos."
    echo "  Revisa la red DDS (ROS_DOMAIN_ID=0) y que la Pi esté accesible."
    exit 1
fi
echo "  /odom OK ✓"

# ── limpiar distancias anteriores ─────────────────────────────────────────────
> "${DIST_FILE}"
echo "# distancias_reales.txt — medidas con cinta métrica (metros)" >> "${DIST_FILE}"
echo "# Generado por run_prueba_recta.sh — $(date)"                 >> "${DIST_FILE}"

# ── loop de 5 pruebas ─────────────────────────────────────────────────────────
for N in $(seq 1 ${N_PRUEBAS}); do
    echo ""
    echo "============================================================"
    echo "  PRUEBA ${N} de ${N_PRUEBAS}"
    echo "============================================================"
    echo "  1. Alinea el robot con la marca de inicio."
    echo ""
    read -rp "  >>> Presiona ENTER cuando estés listo para iniciar..."

    # Iniciar grabación de rosbag en background
    BAG_DIR="${SCRIPT_DIR}/prueba_recta_${N}"
    rm -rf "${BAG_DIR}"
    ros2 bag record /odom /tf -o "${BAG_DIR}" > /tmp/rosbag_recta.log 2>&1 &
    BAG_PID=$!
    echo "  rosbag grabando (PID ${BAG_PID}) → ${BAG_DIR}"
    sleep 1

    # Ejecutar la prueba — salida redirigida al log para no saturar terminal
    echo "  Ejecutando movimiento rectilíneo (~15 s)..."
    python3 "${SCRIPT_DIR}/prueba_recta.py" --prueba "${N}" \
        > /tmp/prueba_recta_live.log 2>&1 || {
        echo "  AVISO: prueba_recta.py terminó con error (¿Ctrl+C?)"
        echo "  Enviando velocidad cero de seguridad..."
        ros2 topic pub --once /diff_cont/cmd_vel_unstamped \
            geometry_msgs/msg/Twist "{}" > /dev/null 2>&1 || true
    }

    # Detener rosbag
    sleep 0.5
    kill "${BAG_PID}" 2>/dev/null || true
    wait "${BAG_PID}" 2>/dev/null || true

    # Mostrar resumen limpio extraído del log
    echo ""
    echo "============================================================"
    echo "  RESULTADO PRUEBA ${N}"
    echo "============================================================"
    grep "Pos\. inicial\|Pos\. final\|Dist\.\|RESULTADOS" /tmp/prueba_recta_live.log \
        | sed 's/.*\] /  /' || true
    echo "============================================================"

    # Solicitar la medición real
    echo ""
    echo "============================================================"
    echo "  >>> ACCIÓN REQUERIDA: MEDIR CON CINTA MÉTRICA"
    echo "============================================================"
    echo "  Mide la distancia real desde la marca de inicio"
    echo "  hasta el eje de las ruedas."
    echo ""
    while true; do
        read -rp "  >>> Ingresa la distancia real en metros (ej: 1.958): " DIST_REAL
        if [[ "${DIST_REAL}" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            break
        else
            echo "  Formato inválido. Usa punto decimal, ej: 1.958"
        fi
    done
    echo "${DIST_REAL}" >> "${DIST_FILE}"
    echo "  ✓ Distancia real ${N}: ${DIST_REAL} m guardada."

    if [ "${N}" -lt "${N_PRUEBAS}" ]; then
        echo ""
        echo "------------------------------------------------------------"
        echo "  Vuelve a posicionar el robot en la marca de inicio."
        echo ""
        read -rp "  >>> Presiona ENTER para continuar con la prueba $((N+1))..."
    fi
done

# ── análisis final ────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  ANÁLISIS FINAL"
echo "============================================================"
python3 "${SCRIPT_DIR}/analizar_prueba_recta.py"

echo ""
echo "=== LISTO ==="
echo "Archivos generados en ${SCRIPT_DIR}:"
echo "  - prueba_recta_{1..5}.log"
echo "  - prueba_recta_{1..5}/   (rosbags)"
echo "  - distancias_reales.txt"
echo "  - tabla_odom_recta_real.tex  ← copiar en 10.resultados.tex"
echo "  - odom_error_barras.pdf/.png ← figura para la tesis"