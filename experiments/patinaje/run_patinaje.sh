#!/usr/bin/env bash
set -euo pipefail

export ROS_DOMAIN_ID=0
unset ROS_LOCALHOST_ONLY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DURACION=90

set +u
source /opt/ros/foxy/setup.bash
source "${SCRIPT_DIR}/../../install/setup.bash"       2>/dev/null || \
source "${HOME}/tesis_black_robot/install/setup.bash" 2>/dev/null || \
source "${HOME}/dev_ws/install/setup.bash"            2>/dev/null || \
{ echo "ERROR: no se encontró install/setup.bash — ajusta la ruta."; exit 1; }
set -u

echo ""
echo "============================================================"
echo "  PRE-REQUISITO: Robot Y mapeo activos"
echo "============================================================"
echo ""
echo "  Este test necesita:"
echo "    1. launch_robot_all.sh corriendo en la Pi"
echo "    2. launch_mapeo_all.sh corriendo en la PC (con SLAM activo)"
echo "    3. TF map→odom ya disponible"
echo ""
echo "    [1] Sí, ambos están activos"
echo "    [2] No — salir"
echo ""
read -rp "  Selecciona una opción [1/2]: " ROBOT_OPT

case "${ROBOT_OPT}" in
    1) ;;
    2|*) exit 0 ;;
esac

echo ""
echo "=== Verificando TF map→odom ==="
ros2 daemon stop > /dev/null 2>&1; sleep 5
ros2 daemon start > /dev/null 2>&1; sleep 3

if timeout 15 ros2 run tf2_ros tf2_echo map odom 2>&1 | grep -q Translation; then
    echo "  TF map→odom OK ✓"
else
    echo "ERROR: TF map→odom no disponible. ¿SLAM Toolbox está activo?"
    exit 1
fi

echo ""
echo "============================================================"
echo "  PROCEDIMIENTO MANUAL DEL OPERADOR"
echo "============================================================"
echo ""
echo "  El test mide la discrepancia entre dos referencias de pose:"
echo "    odom→base_link  (encoders, NO ve obstáculos)"
echo "    map→base_link   (SLAM con fusión LIDAR+odom)"
echo ""
echo "  La discrepancia entre ambas demuestra que SLAM corrige los"
echo "  errores acumulativos de la odometría usando el LIDAR como"
echo "  referencia."
echo ""
echo "  CRONOLOGÍA SUGERIDA (${DURACION}s):"
echo ""
echo "    0 - 15s   →  Robot quieto en posición inicial (baseline)"
echo "   15 - 30s   →  LEVANTA el robot, gira en el aire ~360°,"
echo "                  vuelve a ponerlo en la misma posición física"
echo "                  (esto induce mentira en la odometría)"
echo "   30 - 45s   →  Robot quieto, observa cómo SLAM mantiene map"
echo "                  fiel a la realidad mientras odom queda lejos"
echo "   45 - 60s   →  Muévelo con la mano ~50 cm hacia un lado"
echo "                  (NO con joystick — para inducir patinaje)"
echo "   60 - ${DURACION}s   →  Robot quieto en nueva posición física"
echo ""
echo "  Los eventos no tienen que ser exactos — los marcas tú con"
echo "  tu acción. El script registra la pose cada 1s."
echo ""
read -rp "  >>> Presiona ENTER para iniciar la captura..."

LOG_FILE="${SCRIPT_DIR}/patinaje.csv"

python3 "${SCRIPT_DIR}/medir_patinaje.py" \
    --duracion "${DURACION}" \
    --salida "${LOG_FILE}"

echo ""
echo "============================================================"
echo "  ANÁLISIS"
echo "============================================================"
python3 "${SCRIPT_DIR}/analizar_patinaje.py"

echo ""
echo "=== LISTO ==="
echo "Archivos generados:"
echo "  - patinaje.csv             (pose odom + map cada 1s)"
echo "  - tabla_patinaje.tex       ← copiar en resultados.tex"
echo "  - patinaje_trayectorias.pdf/.png   ← figura: odom vs map"
echo "  - patinaje_error.pdf/.png  ← figura: error vs tiempo"
echo "  - patinaje_resumen.txt     ← resumen humano"