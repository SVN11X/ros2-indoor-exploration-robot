#!/usr/bin/env bash
set -euo pipefail

export ROS_DOMAIN_ID=0
unset ROS_LOCALHOST_ONLY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
N_PRUEBAS=5
DURACION=20

set +u
source /opt/ros/foxy/setup.bash
source "${SCRIPT_DIR}/../../install/setup.bash"       2>/dev/null || \
source "${HOME}/tesis_black_robot/install/setup.bash" 2>/dev/null || \
source "${HOME}/dev_ws/install/setup.bash"            2>/dev/null || \
{ echo "ERROR: no se encontró install/setup.bash — ajusta la ruta."; exit 1; }
set -u

echo ""
echo "============================================================"
echo "  PRE-REQUISITO: Robot activo en la Raspberry Pi"
echo "============================================================"
echo "  ¿Ya lanzaste la pila base del robot en la Pi?"
echo ""
echo "    [1] Sí, usé:  bash ~/robot_ws/scripts/launch/launch_robot_all.sh"
echo "    [2] Sí, usé el modo manual"
echo "    [3] No — salir para lanzarlo primero"
echo ""
read -rp "  Selecciona una opción [1/2/3]: " ROBOT_OPT

case "${ROBOT_OPT}" in
    1) echo "  ✓ Modo automático confirmado." ;;
    2) echo "  ✓ Modo manual confirmado."
       read -rp "  Confirma /scan disponible y presiona ENTER..." ;;
    3|*) echo ""
         echo "  Lanza primero el robot en la Pi:"
         echo "    ssh ubuntu@<IP_ROBOT>"
         echo "    bash ~/robot_ws/scripts/launch/launch_robot_all.sh"
         exit 0 ;;
esac

echo ""
echo "=== Verificando /scan ==="
ros2 daemon stop > /dev/null 2>&1; sleep 5
ros2 daemon start > /dev/null 2>&1; sleep 3

SCAN_FOUND=false
for INTENTO in 1 2 3 4 5; do
    echo "  Intento ${INTENTO}/5..."
    if ros2 topic info /scan 2>/dev/null | grep -qE 'Publisher count: [1-9]'; then
        SCAN_FOUND=true; break
    fi
    sleep 3
done

if [ "${SCAN_FOUND}" = false ]; then
    echo "ERROR: /scan no disponible tras 5 intentos."
    exit 1
fi
echo "  /scan OK ✓"

echo ""
echo "============================================================"
echo "  PROCEDIMIENTO"
echo "============================================================"
echo "  Se ejecutarán ${N_PRUEBAS} capturas independientes de"
echo "  ${DURACION} segundos cada una, con el robot QUIETO en su"
echo "  posición inicial. El análisis estadístico se hará sobre"
echo "  el conjunto de las ${N_PRUEBAS} pruebas."
echo ""
echo "  Mantén el robot inmóvil y el entorno sin movimiento durante"
echo "  toda la duración del test."
echo ""
read -rp "  >>> Presiona ENTER para iniciar..."

for N in $(seq 1 ${N_PRUEBAS}); do
    echo ""
    echo "============================================================"
    echo "  CAPTURA ${N} de ${N_PRUEBAS}  (${DURACION}s)"
    echo "============================================================"
    LOG_FILE="${SCRIPT_DIR}/calidad_lidar_${N}.csv"
    python3 "${SCRIPT_DIR}/medir_calidad_lidar.py" \
        --duracion "${DURACION}" \
        --salida "${LOG_FILE}" \
        --prueba "${N}"
    echo "  ✓ Captura ${N} guardada en calidad_lidar_${N}.csv"

    if [ "${N}" -lt "${N_PRUEBAS}" ]; then
        echo ""
        read -rp "  >>> Presiona ENTER para la captura $((N+1))..."
    fi
done

echo ""
echo "============================================================"
echo "  ANÁLISIS FINAL"
echo "============================================================"
python3 "${SCRIPT_DIR}/analizar_calidad_lidar.py"

echo ""
echo "=== LISTO ==="
echo "Archivos generados en ${SCRIPT_DIR}:"
echo "  - calidad_lidar_{1..${N_PRUEBAS}}.csv      (datos crudos)"
echo "  - tabla_calidad_lidar.tex                  ← copiar en resultados.tex"
echo "  - calidad_lidar_freq.pdf/.png              ← figura: tasa por captura"
echo "  - calidad_lidar_resumen.txt                ← resumen humano"