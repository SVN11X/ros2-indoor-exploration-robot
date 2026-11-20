#!/usr/bin/env bash
set -euo pipefail

export ROS_DOMAIN_ID=0
unset ROS_LOCALHOST_ONLY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

set +u
source /opt/ros/foxy/setup.bash
source "${SCRIPT_DIR}/../../install/setup.bash"       2>/dev/null || \
source "${HOME}/tesis_black_robot/install/setup.bash" 2>/dev/null || \
source "${HOME}/dev_ws/install/setup.bash"            2>/dev/null || \
{ echo "ERROR: no se encontró install/setup.bash — ajusta la ruta."; exit 1; }
set -u

echo ""
echo "============================================================"
echo "  PRE-REQUISITO: SLAM Toolbox activo"
echo "============================================================"
echo "  Necesario:"
echo "    1. launch_robot_all.sh en la Pi"
echo "    2. launch_mapeo_all.sh en la PC con TF map→odom disponible"
echo ""
echo "    [1] Sí, ambos activos"
echo "    [2] No — salir"
echo ""
read -rp "  Selecciona [1/2]: " OPT
case "${OPT}" in
    1) ;;
    *) exit 0 ;;
esac

echo ""
echo "=== Verificando TF map→odom ==="
ros2 daemon stop > /dev/null 2>&1; sleep 5
ros2 daemon start > /dev/null 2>&1; sleep 3
if ! timeout 15 ros2 run tf2_ros tf2_echo map odom 2>&1 | grep -q Translation; then
    echo "ERROR: TF map→odom no disponible. ¿SLAM activo?"
    exit 1
fi
echo "  TF map→odom OK ✓"

echo ""
echo "============================================================"
echo "  PROCEDIMIENTO DEL OPERADOR"
echo "============================================================"
echo ""
echo "  Este test mide el error de cierre de loop, una métrica"
echo "  estándar de calidad en SLAM 2D."
echo ""
echo "  PASOS:"
echo "    1. Marca físicamente en el suelo la posición ACTUAL del"
echo "       robot (con cinta o tiza). Esto es el punto P0."
echo "    2. El script empieza a registrar la pose."
echo "    3. Conduce el robot (joystick o explore) por una"
echo "       trayectoria cerrada de al menos 4-5 metros lineales,"
echo "       idealmente formando un cuadrado o L."
echo "    4. VUELVE al punto P0 marcado, lo más exacto posible"
echo "       (orienta el robot en la misma dirección inicial)."
echo "    5. Presiona ENTER para finalizar el test."
echo ""
echo "  El script calcula:"
echo "    - Distancia total recorrida según SLAM"
echo "    - Error de cierre: ||pose_final - pose_inicial||"
echo "    - Error porcentual relativo a distancia recorrida"
echo ""
read -rp "  >>> Robot en P0. Presiona ENTER para EMPEZAR el registro..."

LOG_FILE="${SCRIPT_DIR}/loop_closure.csv"

python3 "${SCRIPT_DIR}/medir_loop_closure.py" \
    --salida "${LOG_FILE}" &
CAPTURA_PID=$!

echo ""
echo "  ✓ Registro INICIADO. Ahora conduce el robot en trayectoria"
echo "    cerrada y vuelve al punto P0."
echo ""
read -rp "  >>> Cuando hayas vuelto a P0, presiona ENTER para PARAR..."

kill -INT "${CAPTURA_PID}" 2>/dev/null || true
wait "${CAPTURA_PID}" 2>/dev/null || true

echo ""
echo "============================================================"
echo "  ANÁLISIS"
echo "============================================================"
python3 "${SCRIPT_DIR}/analizar_loop_closure.py"

echo ""
echo "=== LISTO ==="
echo "Archivos generados:"
echo "  - loop_closure.csv               (pose continua)"
echo "  - tabla_loop_closure.tex         ← copiar en resultados.tex"
echo "  - loop_closure_trayectoria.pdf/.png  ← figura: trayectoria"
echo "  - loop_closure_resumen.txt       ← resumen humano"