#!/usr/bin/env bash
set -euo pipefail

export ROS_DOMAIN_ID=0
unset ROS_LOCALHOST_ONLY

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DURACION_STRESS=60
DURACION_VENTANA=20

PI_USER="${PI_USER:-ubuntu}"
PI_HOST="${PI_HOST:-192.168.8.211}"

set +u
source /opt/ros/foxy/setup.bash
source "${SCRIPT_DIR}/../../install/setup.bash"       2>/dev/null || \
source "${HOME}/tesis_black_robot/install/setup.bash" 2>/dev/null || \
source "${HOME}/dev_ws/install/setup.bash"            2>/dev/null || \
{ echo "ERROR: no se encontró install/setup.bash — ajusta la ruta."; exit 1; }
set -u

echo ""
echo "============================================================"
echo "  PRE-REQUISITO"
echo "============================================================"
echo "  Robot debe estar corriendo en la Pi (launch_robot_all.sh)"
echo "  La PC debe tener SSH sin contraseña a la Pi."
echo ""
echo "  Pi configurada: ${PI_USER}@${PI_HOST}"
echo "  (puedes sobrescribir con: PI_USER=... PI_HOST=... bash run_stress_cpu.sh)"
echo ""
read -rp "  ¿Confirmas que el robot está corriendo? [y/N]: " RESP
case "${RESP}" in
    [yY]*) ;;
    *) exit 0 ;;
esac

if ! ssh -o ConnectTimeout=5 -o BatchMode=yes "${PI_USER}@${PI_HOST}" 'echo ok' >/dev/null 2>&1; then
    echo "ERROR: no se puede conectar por SSH sin password a ${PI_USER}@${PI_HOST}"
    echo "  Configura ssh-copy-id o ajusta PI_USER/PI_HOST"
    exit 1
fi
echo "  SSH a la Pi OK ✓"

echo ""
echo "=== Verificando topics ==="
ros2 daemon stop > /dev/null 2>&1; sleep 5
ros2 daemon start > /dev/null 2>&1; sleep 3
for T in /scan /odom; do
    if ros2 topic info "${T}" 2>/dev/null | grep -qE 'Publisher count: [1-9]'; then
        echo "  ${T} OK ✓"
    else
        echo "ERROR: ${T} no disponible"
        exit 1
    fi
done

LOG_BASELINE="${SCRIPT_DIR}/stress_baseline.csv"
LOG_STRESS="${SCRIPT_DIR}/stress_durante.csv"
LOG_TERMICO="${SCRIPT_DIR}/stress_termico.csv"

echo ""
echo "============================================================"
echo "  FASE 1/3: BASELINE (sin stress)"
echo "============================================================"
echo "  Capturando ${DURACION_VENTANA}s de tasas en condiciones normales..."

python3 "${SCRIPT_DIR}/medir_stress.py" \
    --duracion "${DURACION_VENTANA}" \
    --salida "${LOG_BASELINE}"

echo ""
echo "============================================================"
echo "  FASE 2/3: DURANTE STRESS"
echo "============================================================"
echo "  Lanzando ${DURACION_STRESS}s de saturación de 4 cores en la Pi..."
echo "  Y midiendo tasas + temp/load en paralelo."
echo ""

ssh "${PI_USER}@${PI_HOST}" "
    echo 't_iso,temp_c,load_1m' > /tmp/pi_termico.csv
    end=\$(( \$(date +%s) + ${DURACION_STRESS} + 5 ))
    while [ \$(date +%s) -lt \$end ]; do
        temp=\$(vcgencmd measure_temp 2>/dev/null | grep -oE '[0-9.]+' | head -1)
        load=\$(uptime | grep -oE 'load average: [^,]+' | sed 's/load average: //' | awk '{print \$1}')
        ts=\$(date +%Y-%m-%dT%H:%M:%S)
        echo \"\$ts,\$temp,\$load\" >> /tmp/pi_termico.csv
        sleep 1
    done
" &
SSH_TERMICO_PID=$!

sleep 2

ssh "${PI_USER}@${PI_HOST}" "timeout ${DURACION_STRESS} bash -c '
    for i in 1 2 3 4; do yes > /dev/null & done
    wait
'" &
SSH_STRESS_PID=$!

sleep 3  # Dejar que el stress arranque

echo "  Stress activo. Midiendo tasas durante ${DURACION_VENTANA}s..."
python3 "${SCRIPT_DIR}/medir_stress.py" \
    --duracion "${DURACION_VENTANA}" \
    --salida "${LOG_STRESS}"

echo "  Esperando que termine el stress (${DURACION_STRESS}s totales)..."
wait "${SSH_STRESS_PID}" 2>/dev/null || true
wait "${SSH_TERMICO_PID}" 2>/dev/null || true

echo "  Descargando log térmico de la Pi..."
scp -q "${PI_USER}@${PI_HOST}:/tmp/pi_termico.csv" "${LOG_TERMICO}" || {
    echo "AVISO: no se pudo descargar log térmico"
}

echo ""
echo "============================================================"
echo "  FASE 3/3: ANÁLISIS"
echo "============================================================"
python3 "${SCRIPT_DIR}/analizar_stress_cpu.py"

echo ""
echo "=== LISTO ==="
echo "Archivos generados:"
echo "  - stress_baseline.csv     (tasas sin stress)"
echo "  - stress_durante.csv      (tasas con stress)"
echo "  - stress_termico.csv      (temp/load de la Pi)"
echo "  - tabla_stress_cpu.tex    ← copiar en resultados.tex"
echo "  - stress_cpu_temp.pdf/.png ← figura temperatura+load"
echo "  - stress_cpu_resumen.txt  ← resumen humano"