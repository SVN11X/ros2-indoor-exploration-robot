#!/usr/bin/env bash
set -euo pipefail

export ROS_DOMAIN_ID=0
unset ROS_LOCALHOST_ONLY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DURACION=60
T_BLOQUEO_INI=20
T_BLOQUEO_FIN=40

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
echo ""
echo "    [1] Sí, usé:  bash ~/robot_ws/scripts/launch/launch_robot_all.sh"
echo "    [2] Sí, usé el modo manual"
echo "    [3] No — salir"
echo ""
read -rp "  Selecciona una opción [1/2/3]: " ROBOT_OPT

case "${ROBOT_OPT}" in
    1) echo "  ✓ Modo automático confirmado." ;;
    2) echo "  ✓ Modo manual confirmado."
       read -rp "  Confirma /scan disponible y presiona ENTER..." ;;
    3|*) exit 0 ;;
esac

echo ""
echo "=== Verificando /scan ==="
ros2 daemon stop > /dev/null 2>&1; sleep 5
ros2 daemon start > /dev/null 2>&1; sleep 3
if ! ros2 topic info /scan 2>/dev/null | grep -qE 'Publisher count: [1-9]'; then
    echo "ERROR: /scan no disponible."
    exit 1
fi
echo "  /scan OK ✓"

echo ""
echo "============================================================"
echo "  PROCEDIMIENTO MANUAL DEL OPERADOR"
echo "============================================================"
echo ""
echo "  Esta prueba inyecta un fallo controlado en el LIDAR para"
echo "  verificar que el sistema detecta la obstrucción."
echo ""
echo "  CRONOLOGÍA DEL TEST (${DURACION}s en total):"
echo ""
echo "    0 - ${T_BLOQUEO_INI}s   →  LIDAR libre (mide baseline)"
echo "   ${T_BLOQUEO_INI} - ${T_BLOQUEO_FIN}s  →  LIDAR BLOQUEADO con cartón a ~25 cm"
echo "   ${T_BLOQUEO_FIN} - ${DURACION}s  →  LIDAR libre de nuevo (mide recuperación)"
echo ""
echo "  IMPORTANTE: el cartón debe estar a 20-30 cm del sensor,"
echo "  NO pegado (porque a <15 cm cae bajo range_min y se filtra"
echo "  como inf, lo que se confundiría con falla del lidar)."
echo ""
echo "  El script te avisará por audio cuando bloquear y cuando"
echo "  retirar el cartón."
echo ""
read -rp "  >>> Presiona ENTER para iniciar..."

LOG_FILE="${SCRIPT_DIR}/bloqueo_lidar.csv"

(
    sleep "${T_BLOQUEO_INI}"
    echo ""
    echo "    >>> AHORA: BLOQUEA el LIDAR con el cartón a ~25 cm <<<"

    printf '\a' 2>/dev/null || true

    sleep $((T_BLOQUEO_FIN - T_BLOQUEO_INI))
    echo ""
    echo "    >>> AHORA: RETIRA el cartón <<<"
    printf '\a' 2>/dev/null || true
) &
AVISO_PID=$!

python3 "${SCRIPT_DIR}/medir_bloqueo_lidar.py" \
    --duracion "${DURACION}" \
    --salida "${LOG_FILE}"

kill "${AVISO_PID}" 2>/dev/null || true
wait "${AVISO_PID}" 2>/dev/null || true

echo ""
echo "============================================================"
echo "  ANÁLISIS"
echo "============================================================"
python3 "${SCRIPT_DIR}/analizar_bloqueo_lidar.py" \
    --t-bloqueo-ini "${T_BLOQUEO_INI}" \
    --t-bloqueo-fin "${T_BLOQUEO_FIN}"

echo ""
echo "=== LISTO ==="
echo "Archivos generados:"
echo "  - bloqueo_lidar.csv             (datos crudos por scan)"
echo "  - tabla_bloqueo_lidar.tex       ← copiar en resultados.tex"
echo "  - bloqueo_lidar_temporal.pdf/.png ← figura: % válidos vs tiempo"
echo "  - bloqueo_lidar_resumen.txt     ← resumen humano"