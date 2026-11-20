#!/bin/bash
# ============================================================
# check_gpio_lidar.sh  (v2 — con test activo de protocolo)
# Diagnóstico de comunicación GPIO/UART entre Pi y RPLidar A1
# ============================================================

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   DIAGNÓSTICO GPIO/UART LIDAR ↔ PI       ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

BLOCKERS_FOUND=0

# Detectar ruta de config.txt (Ubuntu 20.04 vs Raspberry Pi OS)
if [ -f /boot/firmware/config.txt ]; then
    CONFIG_TXT=/boot/firmware/config.txt
    CMDLINE_TXT=/boot/firmware/cmdline.txt
elif [ -f /boot/config.txt ]; then
    CONFIG_TXT=/boot/config.txt
    CMDLINE_TXT=/boot/cmdline.txt
else
    CONFIG_TXT=""
    CMDLINE_TXT=""
fi

# -----------------------------------------------------------
# 1. UART habilitada y PL011 mapeada a los GPIO
# -----------------------------------------------------------
echo -e "${CYAN}[1/9] UART habilitada y PL011 sobre GPIO 14/15${NC}"
echo "----------------------------------------------"

if [ -z "$CONFIG_TXT" ]; then
    echo -e "  ${RED}❌ No se encontró config.txt${NC}"
    BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
else
    echo "  Usando: $CONFIG_TXT"

    if grep -qE "^enable_uart=1" "$CONFIG_TXT"; then
        echo -e "  ${GREEN}✅ enable_uart=1 presente${NC}"
    else
        echo -e "  ${RED}❌ enable_uart=1 NO está habilitado${NC}"
        BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
    fi

    if grep -qE "^dtoverlay=disable-bt|^dtoverlay=pi3-disable-bt" "$CONFIG_TXT"; then
        echo -e "  ${GREEN}✅ Bluetooth deshabilitado (PL011 libre para GPIO)${NC}"
    else
        echo -e "  ${YELLOW}⚠️  dtoverlay=disable-bt NO está presente${NC}"
        echo "     (No crítico si el test de protocolo del paso [9/9] pasa.)"
    fi
fi

# Verificar a qué UART apuntan los GPIO 14/15 (si raspi-gpio está disponible)
if command -v raspi-gpio &>/dev/null; then
    GPIO14_FUNC=$(raspi-gpio get 14 2>/dev/null | grep -oE 'func=[A-Z0-9]+' | cut -d= -f2)
    GPIO15_FUNC=$(raspi-gpio get 15 2>/dev/null | grep -oE 'func=[A-Z0-9]+' | cut -d= -f2)
    echo "  GPIO 14 (TXD): $GPIO14_FUNC    GPIO 15 (RXD): $GPIO15_FUNC"
    if [ "$GPIO14_FUNC" = "ALT0" ] && [ "$GPIO15_FUNC" = "ALT0" ]; then
        echo -e "  ${GREEN}✅ GPIO 14/15 en ALT0 (UART0/PL011) — correcto${NC}"
    elif [ "$GPIO14_FUNC" = "ALT5" ] && [ "$GPIO15_FUNC" = "ALT5" ]; then
        echo -e "  ${YELLOW}⚠️  GPIO 14/15 en ALT5 (mini UART) — inestable a 115200${NC}"
    fi
fi

if [ -L /dev/serial0 ]; then
    SERIAL0_TARGET=$(readlink -f /dev/serial0)
    echo -e "  ${CYAN}/dev/serial0 → $SERIAL0_TARGET${NC}"
fi
echo ""

# -----------------------------------------------------------
# 2. Console serial deshabilitada en cmdline.txt
# -----------------------------------------------------------
echo -e "${CYAN}[2/9] Consola serial deshabilitada en cmdline.txt${NC}"
echo "----------------------------------------------"

if [ -z "$CMDLINE_TXT" ] || [ ! -f "$CMDLINE_TXT" ]; then
    echo -e "  ${YELLOW}⚠️  No se encontró cmdline.txt${NC}"
else
    if grep -qE "console=(serial0|ttyAMA0|ttyS0)" "$CMDLINE_TXT"; then
        echo -e "  ${RED}❌ Hay una consola serial activa${NC}"
        grep -oE "console=(serial0|ttyAMA0|ttyS0)[^ ]*" "$CMDLINE_TXT" | sed 's/^/     → /'
        BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
    else
        echo -e "  ${GREEN}✅ No hay consola serial activa${NC}"
    fi
fi
echo ""

# -----------------------------------------------------------
# 3. Dispositivo /dev/ttyAMA0 presente y permisos
# -----------------------------------------------------------
echo -e "${CYAN}[3/9] Dispositivo /dev/ttyAMA0${NC}"
echo "----------------------------------------------"

if [ -c /dev/ttyAMA0 ]; then
    TTY_INFO=$(ls -la /dev/ttyAMA0 | awk '{print $1, $3, $4}')
    echo -e "  ${GREEN}✅ /dev/ttyAMA0 existe${NC}"
    echo "     Permisos: $TTY_INFO"

    TTY_GROUP=$(stat -c %G /dev/ttyAMA0 2>/dev/null)
    if [ "$TTY_GROUP" = "dialout" ] || [ "$TTY_GROUP" = "root" ]; then
        echo -e "  ${GREEN}✅ Grupo: $TTY_GROUP${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Grupo: $TTY_GROUP (debería ser dialout o root)${NC}"
    fi
else
    echo -e "  ${RED}❌ /dev/ttyAMA0 NO existe${NC}"
    BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
fi
echo ""

# -----------------------------------------------------------
# 4. Symlink /dev/rlidar_gpio (regla udev)
# -----------------------------------------------------------
echo -e "${CYAN}[4/9] Symlink /dev/rlidar_gpio (regla udev)${NC}"
echo "----------------------------------------------"

if [ -L /dev/rlidar_gpio ]; then
    RLIDAR_TARGET=$(readlink -f /dev/rlidar_gpio)
    echo -e "  ${GREEN}✅ /dev/rlidar_gpio → $RLIDAR_TARGET${NC}"
else
    echo -e "  ${RED}❌ /dev/rlidar_gpio NO existe${NC}"
    BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
fi
echo ""

# -----------------------------------------------------------
# 5. Pertenencia del usuario al grupo dialout
# -----------------------------------------------------------
echo -e "${CYAN}[5/9] Pertenencia al grupo dialout${NC}"
echo "----------------------------------------------"

if groups | grep -q "dialout"; then
    echo -e "  ${GREEN}✅ Tu usuario pertenece al grupo dialout${NC}"
else
    echo -e "  ${RED}❌ No estás en el grupo dialout${NC}"
    BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
fi
echo ""

# -----------------------------------------------------------
# 6. Errores del kernel relacionados con UART
# -----------------------------------------------------------
echo -e "${CYAN}[6/9] Errores del kernel relacionados con UART${NC}"
echo "----------------------------------------------"

DMESG_UART=$(dmesg 2>/dev/null | grep -iE "ttyAMA|amba.*uart|pl011|serial.*error" | tail -10)

if [ -z "$DMESG_UART" ]; then
    echo -e "  ${GREEN}✅ Sin mensajes de UART en el kernel${NC}"
else
    DMESG_BAD=$(echo "$DMESG_UART" | grep -iE "error|fail|timeout|disabled")
    if [ -z "$DMESG_BAD" ]; then
        echo -e "  ${GREEN}✅ Solo mensajes informativos (no errores):${NC}"
        echo "$DMESG_UART" | tail -3 | sed 's/^/     /'
    else
        echo -e "  ${RED}❌ Errores detectados:${NC}"
        echo "$DMESG_BAD" | sed 's/^/     /'
        BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
    fi
fi
echo ""

# -----------------------------------------------------------
# 7. Procesos bloqueando el puerto serie
# -----------------------------------------------------------
echo -e "${CYAN}[7/9] Procesos bloqueando /dev/ttyAMA0${NC}"
echo "----------------------------------------------"

LSOF_OUT=$(sudo lsof /dev/ttyAMA0 2>/dev/null)
if [ -n "$LSOF_OUT" ]; then
    echo -e "  ${YELLOW}⚠️  Hay procesos usando el puerto:${NC}"
    echo "$LSOF_OUT" | head -10 | sed 's/^/     /'
    BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
else
    echo -e "  ${GREEN}✅ Puerto libre (sin procesos bloqueándolo)${NC}"
fi

if systemctl is-active --quiet hciuart 2>/dev/null; then
    echo -e "  ${YELLOW}⚠️  hciuart activo (puede ocupar el PL011 sin disable-bt)${NC}"
fi
echo ""

# -----------------------------------------------------------
# 8. Configuración del puerto serie (informativo, NO blocker)
# -----------------------------------------------------------
echo -e "${CYAN}[8/9] Configuración stty del puerto (informativo)${NC}"
echo "----------------------------------------------"

if [ -c /dev/ttyAMA0 ]; then
    STTY_OUT=$(sudo stty -F /dev/ttyAMA0 -a 2>/dev/null)
    if [ -n "$STTY_OUT" ]; then
        echo "$STTY_OUT" | grep -E "speed|icanon|echo" | head -2 | sed 's/^/  /'
        echo -e "  ${YELLOW}ℹ️  El driver \"rplidar_ros\" reconfigura el puerto al iniciar,${NC}"
        echo -e "  ${YELLOW}   así que estos valores no son críticos. El test [9/9]${NC}"
        echo -e "  ${YELLOW}   también configura el puerto antes de probar.${NC}"
    fi
fi
echo ""

# -----------------------------------------------------------
# 9. Test ACTIVO de protocolo: enviar GET_INFO + GET_HEALTH
#    y verificar respuesta del RPLidar A1
# -----------------------------------------------------------
echo -e "${CYAN}[9/9] Test activo de protocolo RPLidar (handshake)${NC}"
echo "----------------------------------------------"

if [ ! -c /dev/ttyAMA0 ]; then
    echo -e "  ${RED}❌ /dev/ttyAMA0 no existe; no se pudo probar${NC}"
    BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
else
    # Crear helper Python temporal con el handshake del protocolo RPLidar A1
    HELPER=$(mktemp /tmp/rplidar_handshake.XXXXXX.py)
    cat > "$HELPER" << 'PYEOF'
#!/usr/bin/env python3
"""
Handshake activo con RPLidar A1 vía protocolo serial.
Envía STOP, luego GET_INFO y GET_HEALTH, y parsea las respuestas.
Salida en stdout en formato 'KEY=VALUE' fácil de parsear por bash.
Códigos de salida:
  0 - éxito completo
  2 - no se pudo abrir el puerto
  3 - sin respuesta (probable TX/RX cruzados, motor apagado o cable)
  4 - respuesta parcial (probable conexión intermitente)
  5 - descriptor inválido (no parece un RPLidar)
"""
import os, sys, time, termios, select

PORT = '/dev/ttyAMA0'

try:
    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY)
except OSError as e:
    print(f"ERR=open:{e}")
    sys.exit(2)

# Configurar UART en raw 115200 8N1 sin eco ni control de flujo
attrs = termios.tcgetattr(fd)
attrs[0] = 0
attrs[1] = 0
attrs[2] = termios.CS8 | termios.CLOCAL | termios.CREAD
attrs[3] = 0
attrs[4] = termios.B115200
attrs[5] = termios.B115200
attrs[6][termios.VMIN]  = 0
attrs[6][termios.VTIME] = 1
termios.tcsetattr(fd, termios.TCSANOW, attrs)

def read_n(n, timeout):
    buf = b''
    deadline = time.time() + timeout
    while len(buf) < n:
        rem = deadline - time.time()
        if rem <= 0: break
        r, _, _ = select.select([fd], [], [], rem)
        if not r: break
        chunk = os.read(fd, n - len(buf))
        if not chunk: break
        buf += chunk
    return buf

# Limpiar estado: enviar STOP, esperar, drenar
os.write(fd, b'\xA5\x25')
time.sleep(0.1)
termios.tcflush(fd, termios.TCIFLUSH)

# ----- GET_INFO -----
os.write(fd, b'\xA5\x50')
resp = read_n(7 + 20, timeout=1.5)

if len(resp) == 0:
    print("ERR=no_response_info")
    os.close(fd); sys.exit(3)
if len(resp) < 7:
    print(f"ERR=partial_info:{resp.hex()}")
    os.close(fd); sys.exit(4)
if resp[0] != 0xA5 or resp[1] != 0x5A:
    print(f"ERR=bad_descriptor_info:{resp[:8].hex()}")
    os.close(fd); sys.exit(5)
if len(resp) < 27:
    print(f"ERR=short_payload_info:got={len(resp)}")
    os.close(fd); sys.exit(4)

# Parsear payload de GET_INFO (20 bytes): model, fw_minor, fw_major, hw, serial[16]
model    = resp[7]
fw_minor = resp[8]
fw_major = resp[9]
hw_ver   = resp[10]
serial   = resp[11:27].hex().upper()

print(f"INFO_MODEL={model}")
print(f"INFO_FW={fw_major}.{fw_minor:02d}")
print(f"INFO_HW={hw_ver}")
print(f"INFO_SERIAL={serial}")

# ----- GET_HEALTH -----
time.sleep(0.05)
termios.tcflush(fd, termios.TCIFLUSH)
os.write(fd, b'\xA5\x52')
resp = read_n(7 + 3, timeout=1.0)

if len(resp) < 10 or resp[0] != 0xA5 or resp[1] != 0x5A:
    print(f"ERR=bad_health:{resp.hex()}")
    os.close(fd); sys.exit(5)

status_map = {0: "Good", 1: "Warning", 2: "Error"}
status     = resp[7]
err_code   = resp[8] | (resp[9] << 8)

print(f"HEALTH_STATUS={status_map.get(status, f'Unknown({status})')}")
print(f"HEALTH_CODE={err_code}")

os.close(fd)
sys.exit(0)
PYEOF

    echo -e "  ${YELLOW}Enviando comandos al LiDAR (GET_INFO + GET_HEALTH)...${NC}"

    RAW=$(sudo python3 "$HELPER" 2>&1)
    RC=$?
    rm -f "$HELPER"

    case $RC in
        0)
            echo -e "  ${GREEN}✅ HANDSHAKE COMPLETADO — el LiDAR responde correctamente${NC}"
            echo ""
            echo "  Información del dispositivo:"
            echo "$RAW" | grep -E "^INFO_|^HEALTH_" | sed 's/^/     /'

            HEALTH_STATUS=$(echo "$RAW" | grep "^HEALTH_STATUS=" | cut -d= -f2)
            if [ "$HEALTH_STATUS" = "Good" ]; then
                echo ""
                echo -e "  ${GREEN}✅ Estado de salud: Good — el LiDAR está operativo${NC}"
            else
                echo ""
                echo -e "  ${YELLOW}⚠️  Estado de salud: $HEALTH_STATUS${NC}"
                echo "     Revisa el código de error reportado arriba."
            fi
            ;;
        2)
            echo -e "  ${RED}❌ No se pudo abrir /dev/ttyAMA0${NC}"
            echo "$RAW" | sed 's/^/     /'
            BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
            ;;
        3)
            echo -e "  ${RED}❌ No hubo respuesta del LiDAR${NC}"
            echo ""
            echo "  El TX del Pi llegó al puerto, pero no volvió nada por RX."
            echo "  Causas más probables (en orden):"
            echo "    1. RX y TX cruzados al revés. Verifica:"
            echo "       - TX lidar (amarillo) → Pin 10 RPi (RXD)"
            echo "       - RX lidar (verde)    → Pin 8  RPi (TXD)"
            echo "    2. El motor del LiDAR no está alimentado:"
            echo "       - 5V_MOTO (rojo)   → Pin 2 RPi"
            echo "       - GND_MOTO (negro) → Pin 9 RPi"
            echo "       - CTRL_MOTO (azul) → Pin 1 RPi (3.3V para girar)"
            echo "    3. El PL011 no está realmente sobre GPIO 14/15 (mira paso [1/9])"
            BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
            ;;
        4)
            echo -e "  ${YELLOW}⚠️  Respuesta parcial — conexión intermitente${NC}"
            echo "$RAW" | sed 's/^/     /'
            echo ""
            echo "  Algo de comunicación funciona pero se pierde. Causas posibles:"
            echo "    1. Cable de datos suelto o de mala calidad."
            echo "    2. GND mal conectado (revisa AMBOS: lógica + motor)."
            echo "    3. Mini UART en vez de PL011 (revisa paso [1/9])."
            BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
            ;;
        5)
            echo -e "  ${YELLOW}⚠️  Respuesta inválida — bytes no coinciden con protocolo RPLidar${NC}"
            echo "$RAW" | sed 's/^/     /'
            echo ""
            echo "  Llegaron bytes pero no son del protocolo RPLidar. Causas posibles:"
            echo "    1. Ruido eléctrico en las líneas TX/RX."
            echo "    2. El dispositivo conectado no es un RPLidar (otro adaptador serial)."
            echo "    3. Baudrate equivocado del lado del lidar (debe ser 115200)."
            BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
            ;;
        *)
            echo -e "  ${RED}❌ Error inesperado (rc=$RC):${NC}"
            echo "$RAW" | sed 's/^/     /'
            BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
            ;;
    esac
fi
echo ""

# -----------------------------------------------------------
# Resumen final
# -----------------------------------------------------------
echo "╔══════════════════════════════════════════════╗"
echo "║   RESUMEN FINAL                           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

if [ $BLOCKERS_FOUND -eq 0 ]; then
    echo -e "  ${GREEN}✅ CONEXIÓN GPIO/UART OPERATIVA — VERIFICADA CON PROTOCOLO${NC}"
    echo ""
    echo "  Todos los pasos pasaron, incluyendo el handshake activo con el LiDAR."
    echo "  Puedes lanzar el nodo ROS con certeza de que la capa física funciona:"
    echo ""
    echo "     ros2 launch articubot_one rplidar.launch.py"
    echo ""
    echo "  Asegúrate de que 'serial_port' en tu launch apunte a /dev/rlidar_gpio."
else
    echo -e "  ${RED}❌ Se detectaron $BLOCKERS_FOUND problema(s) reales en la conexión GPIO.${NC}"
    echo ""
    echo "  Revisa los mensajes marcados en rojo arriba — especialmente el paso [9/9]"
    echo "  que indica EXACTAMENTE qué falla en el handshake con el LiDAR."
fi

echo ""
echo "  Puerto UART:           /dev/ttyAMA0 ($([ -c /dev/ttyAMA0 ] && echo 'presente' || echo 'ausente'))"
echo "  Symlink LiDAR:         $([ -L /dev/rlidar_gpio ] && readlink -f /dev/rlidar_gpio || echo 'no existe')"
echo "  Grupo dialout:         $(groups | grep -q dialout && echo 'OK' || echo 'falta')"
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   DIAGNÓSTICO COMPLETADO                  ║"
echo "╚══════════════════════════════════════════════╝"