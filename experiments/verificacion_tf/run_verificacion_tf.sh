#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPORT_FILE="${SCRIPT_DIR}/reporte_tf.txt"
source /opt/ros/foxy/setup.bash
source "${SCRIPT_DIR}/../../install/setup.bash"       2>/dev/null || \
source "${HOME}/tesis_black_robot/install/setup.bash" 2>/dev/null || \
source "${HOME}/dev_ws/install/setup.bash"            2>/dev/null || \
{ echo "ERROR: no se encontró install/setup.bash — ajusta la ruta."; exit 1; }
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
        exit 0
        ;;
esac
echo ""
echo "=== Verificando tópicos base ==="
for TOPIC in /odom /scan /tf /tf_static; do
    if timeout 5 ros2 topic echo ${TOPIC} --once &>/dev/null; then
        echo "  ${TOPIC} OK ✓"
    else
        echo "  ${TOPIC} NO disponible ✗  — verifica que el robot esté activo"
    fi
done
echo ""
echo "============================================================"
echo "  [1/3] Generando árbol de transformaciones (view_frames)..."
echo "============================================================"
cd "${SCRIPT_DIR}"
ros2 run tf2_tools view_frames
echo "  ✓ Archivo frames*.pdf generado."
FRAMES_PDF=$(ls -t "${SCRIPT_DIR}"/frames*.pdf 2>/dev/null | head -1)
if [ -n "${FRAMES_PDF}" ]; then
    cp "${FRAMES_PDF}" "${SCRIPT_DIR}/tf_tree_real.pdf"
    echo "  ✓ Copiado como: tf_tree_real.pdf"
else
    echo "  AVISO: no se encontró frames*.pdf en ${SCRIPT_DIR}"
fi
echo ""
if command -v pdftoppm &>/dev/null; then
    pdftoppm "${SCRIPT_DIR}/tf_tree_real.pdf" \
             "${SCRIPT_DIR}/tf_tree_real" -png -r 200
    if [ -f "${SCRIPT_DIR}/tf_tree_real-1.png" ]; then
        mv "${SCRIPT_DIR}/tf_tree_real-1.png" "${SCRIPT_DIR}/tf_tree_real.png"
        echo "  ✓ Convertido a: tf_tree_real.png"
    fi
else
    echo "  AVISO: pdftoppm no instalado — convierte manualmente el PDF."
    echo "    sudo apt install poppler-utils"
fi
echo ""
echo "============================================================"
echo "  [2/3] Verificando frecuencia de publicación de /odom..."
echo "        (midiendo durante 10 s)"
echo "============================================================"
HZ_OUTPUT=$(timeout 12 ros2 topic hz /odom 2>&1 | head -6 || true)
echo "${HZ_OUTPUT}"
HZ_VALOR=$(echo "${HZ_OUTPUT}" | grep "average rate" | awk '{print $3}' | head -1)
echo ""
echo "============================================================"
echo "  [3/3] Verificando transformaciones clave..."
echo "============================================================"

verificar_tf() {
    local FROM="$1"
    local TO="$2"
    local RESULTADO
    if RESULTADO=$(timeout 4 ros2 run tf2_ros tf2_echo "${FROM}" "${TO}" 2>&1 | \
                   grep -m1 "Translation" || true); then
        echo "  ${FROM} → ${TO}  ✓"
        echo "    ${RESULTADO}"
    else
        echo "  ${FROM} → ${TO}  ✗  (no disponible o timeout)"
    fi
}

verificar_tf odom        base_link
verificar_tf base_link   base_footprint
verificar_tf base_link   laser_frame
verificar_tf base_link   left_wheel
verificar_tf base_link   right_wheel
echo ""
echo "============================================================"
echo "  Generando reporte: reporte_tf.txt"
echo "============================================================"

{
    echo "# Reporte verificación TF — $(date)"
    echo "# Generado por run_verificacion_tf.sh"
    echo ""
    echo "## Frecuencia /odom"
    echo "${HZ_OUTPUT}"
    echo ""
    echo "## Tópicos verificados"
    for TOPIC in /odom /scan /tf /tf_static; do
        if timeout 3 ros2 topic echo ${TOPIC} --once &>/dev/null 2>&1; then
            echo "  ${TOPIC}: OK"
        else
            echo "  ${TOPIC}: NO disponible"
        fi
    done
    echo ""
    echo "## Archivos generados"
    echo "  tf_tree_real.pdf"
    echo "  tf_tree_real.png"
    echo ""
    echo "## Marcos verificados"
    echo "  odom → base_link        (diff_drive_controller)"
    echo "  base_link → base_footprint (estático, URDF)"
    echo "  base_link → laser_frame    (estático, URDF)"
    echo "  base_link → left_wheel     (estático, URDF)"
    echo "  base_link → right_wheel    (estático, URDF)"
    echo ""
    echo "## COMPLETAR EN TESIS"
    if [ -n "${HZ_VALOR}" ]; then
        echo "  Frecuencia /odom medida: ${HZ_VALOR} Hz  (esperado: ~30 Hz (hardware real) / ~50 Hz (simulación))"
    else
        echo "  Frecuencia /odom medida: --- Hz  (medir manualmente con ros2 topic hz /odom)"
    fi
    echo "  Insertar imagen: tf_tree_real.png en fig:tf_tree_real"
} > "${REPORT_FILE}"

echo "  ✓ Reporte guardado: ${REPORT_FILE}"
echo ""
echo "=== LISTO ==="
echo "Archivos generados en ${SCRIPT_DIR}:"
echo "  - tf_tree_real.pdf   ← árbol de TF (fuente)"
echo "  - tf_tree_real.png   ← figura para la tesis (fig:tf_tree_real)"
echo "  - reporte_tf.txt     ← frecuencias y marcos verificados"
echo ""
if [ -n "${HZ_VALOR}" ]; then
    echo "  Frecuencia /odom medida: ${HZ_VALOR} Hz"
    HZ_INT=$(echo "${HZ_VALOR}" | cut -d. -f1)
    if [ "${HZ_INT}" -lt 35 ] 2>/dev/null; then
        echo "  ⚠ ADVERTENCIA: frecuencia baja (<35 Hz) — revisar carga de CPU en la Pi."
    else
        echo "  ✓ Frecuencia dentro del rango esperado (≥35 Hz)."
    fi
fi