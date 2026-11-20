#!/usr/bin/env bash
# ============================================================
# run_prueba_giro.sh — Orquestador de la prueba de giro 360°
#   (5 repeticiones, 0.5 rad/s, ~12.57 s)
#
# USO (desde la PC, con el robot ya encendido vía SSH):
#   bash ~/tesis_black_robot/experiments/prueba_giro/run_prueba_giro.sh
# ============================================================
set -euo pipefail

# FIX: Garantizar entorno DDS
export ROS_DOMAIN_ID=0
unset ROS_LOCALHOST_ONLY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ANGULO_FILE="${SCRIPT_DIR}/angulos_reales.txt"
N_PRUEBAS=5

# ── fuentes ROS2 ─────────────────────────────────────────────────────────────
# FIX: set +u evita "unbound variable" en scripts de ROS/colcon
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
        exit 0
        ;;
esac

# ── verificar /odom ───────────────────────────────────────────────────────────
echo ""
echo "=== Verificando /odom ==="
# FIX: Limpiar daemon rancio + usar topic list (Foxy no soporta --once)
ros2 daemon stop > /dev/null 2>&1; sleep 3
if ! timeout 10 ros2 topic list 2>/dev/null | grep -q "/odom"; then
    echo "ERROR: /odom no disponible."
    echo "  Revisa la red DDS (ROS_DOMAIN_ID=0) y que la Pi esté accesible."
    exit 1
fi
echo "  /odom OK ✓"

# ── instrucciones de medición ─────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  INSTRUCCIONES DE MEDICIÓN"
echo "============================================================"
echo "  Necesitarás medir el ángulo real tras cada giro."
echo "  Métodos recomendados:"
echo "    a) Transportador apoyado en la marca del suelo vs. frente del robot."
echo "    b) Fotografía cenital + medición en software (ej: GIMP, ImageJ)."
echo "  Anota el ángulo TOTAL girado (debería ser ~360°, puede ser 355° o 368°)."
echo ""
read -rp "  >>> Presiona ENTER para continuar..."

# ── limpiar archivo de ángulos anteriores ──────────────────────────────────────
> "${ANGULO_FILE}"
echo "# angulos_reales.txt — ángulo real medido físicamente (grados)" >> "${ANGULO_FILE}"
echo "# Generado por run_prueba_giro.sh — $(date)"                    >> "${ANGULO_FILE}"

# ── loop de 5 pruebas ─────────────────────────────────────────────────────────
for N in $(seq 1 ${N_PRUEBAS}); do
    echo ""
    echo "============================================================"
    echo "  PRUEBA ${N} de ${N_PRUEBAS}"
    echo "============================================================"
    echo "  1. Coloca el robot en zona despejada (≥0,5 m libres)."
    echo "  2. Alinea el frente del robot con la marca de inicio."
    echo ""
    read -rp "  >>> Presiona ENTER cuando estés listo para iniciar..."

    # Iniciar grabación de rosbag en background (salida redirigida)
    BAG_DIR="${SCRIPT_DIR}/prueba_giro_${N}"
    rm -rf "${BAG_DIR}"
    ros2 bag record /odom /tf -o "${BAG_DIR}" > /tmp/rosbag_giro.log 2>&1 &
    BAG_PID=$!
    echo "  rosbag grabando → ${BAG_DIR}"
    sleep 1

    # Ejecutar la prueba — salida redirigida al log para no saturar terminal
    echo "  Ejecutando giro 360° (~13 s)..."
    python3 "${SCRIPT_DIR}/prueba_giro.py" --prueba "${N}" \
        > /tmp/prueba_giro_live.log 2>&1 || {
        echo "  AVISO: prueba_giro.py terminó con error (¿Ctrl+C?)"
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
    grep "Yaw inicial\|Yaw final\|Giro acumulado\|RESULTADOS" /tmp/prueba_giro_live.log \
        | sed 's/.*\] /  /' || true
    echo "============================================================"

    # Solicitar medición física del ángulo real
    echo ""
    echo "============================================================"
    echo "  >>> ACCIÓN REQUERIDA: MEDIR ÁNGULO CON TRANSPORTADOR"
    echo "============================================================"
    echo "  Mide el ángulo total girado respecto a la marca de inicio."
    echo "  (debería ser ~360°, puede ser 355° o 368°)"
    echo ""
    while true; do
        read -rp "  >>> Ingresa el ángulo real en grados (ej: 366.2): " ANG_REAL
        if [[ "${ANG_REAL}" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
            break
        else
            echo "  Formato inválido. Usa punto decimal, ej: 366.2"
        fi
    done
    echo "${ANG_REAL}" >> "${ANGULO_FILE}"
    DERIVA=$(echo "${ANG_REAL} - 360" | bc -l)
    echo "  ✓ Ángulo real ${N}: ${ANG_REAL}° guardado (deriva: ${DERIVA}°)."

    if [ "${N}" -lt "${N_PRUEBAS}" ]; then
        echo ""
        echo "------------------------------------------------------------"
        echo "  Vuelve a alinear el robot con la marca de inicio."
        echo ""
        read -rp "  >>> Presiona ENTER para continuar con la prueba $((N+1))..."
    fi
done

# ── análisis final ────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo "  ANÁLISIS FINAL"
echo "============================================================"
python3 "${SCRIPT_DIR}/analizar_prueba_giro.py"

echo ""
echo "=== LISTO ==="
echo "Archivos generados en ${SCRIPT_DIR}:"
echo "  - prueba_giro_{1..5}.log"
echo "  - prueba_giro_{1..5}/    (rosbags)"
echo "  - angulos_reales.txt"
echo "  - tabla_odom_giro_real.tex   ← copiar en 10.resultados.tex"
echo "  - giro_deriva_barras.pdf/.png ← figura para la tesis"
echo ""
echo "  Si la deriva media es >15°, revisar:"
echo "    wheel_separation: 0.188 en ~/robot_ws/src/articubot_one/config/my_controllers.yaml"