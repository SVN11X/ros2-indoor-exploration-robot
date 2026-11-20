#!/bin/bash
# ============================================================
# check_usb_lidar.sh
# Diagnóstico específico de comunicación USB entre Pi y RPLidar
# ============================================================

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   DIAGNÓSTICO USB LIDAR ↔ RASPBERRY PI    ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

USB_DEVICE=""
CP210X_FOUND=0
BLOCKERS_FOUND=0

# -----------------------------------------------------------
# 1. Verificar si el dispositivo USB del LiDAR está presente
# -----------------------------------------------------------
echo -e "${CYAN}[1/8] Presencia del adaptador USB-Serial CP210x${NC}"
echo "----------------------------------------------"

# Buscar dispositivo por vendor/product ID
USB_DEVICE=$(lsusb -d 10c4:ea60 2>/dev/null)

if [ -n "$USB_DEVICE" ]; then
    echo -e "  ${GREEN}✅ Adaptador CP210x detectado:${NC}"
    echo "     $USB_DEVICE"
    
    # Obtener el bus y dispositivo
    BUS=$(echo "$USB_DEVICE" | awk '{print $2}')
    DEV=$(echo "$USB_DEVICE" | awk '{print $4}' | sed 's/://')
    echo "     Bus: $BUS  Dispositivo: $DEV"
    CP210X_FOUND=1
else
    echo -e "  ${RED}❌ Adaptador CP210x NO detectado${NC}"
    echo "     ¿Está el LiDAR conectado por USB?"
    echo "     Verifica el cable y prueba otro puerto USB."
    echo ""
    echo "  Saltando el resto de pruebas..."
    exit 1
fi
echo ""

# -----------------------------------------------------------
# 2. Verificar qué puerto serie (ttyUSB) está asignado
# -----------------------------------------------------------
echo -e "${CYAN}[2/8] Puerto serie asignado (ttyUSB)${NC}"
echo "----------------------------------------------"

TTY_USB=$(ls -la /dev/serial/by-path/ 2>/dev/null | grep "usb" | grep -oP 'ttyUSB[0-9]+' | head -1)

if [ -n "$TTY_USB" ]; then
    echo -e "  ${GREEN}✅ Puerto serie: /dev/$TTY_USB${NC}"
    
    # Verificar permisos
    TTY_PERMS=$(ls -la /dev/$TTY_USB 2>/dev/null | awk '{print $1, $3, $4}')
    echo "     Permisos: $TTY_PERMS"
    
    # Verificar grupo
    TTY_GROUP=$(stat -c %G /dev/$TTY_USB 2>/dev/null)
    if [ "$TTY_GROUP" = "dialout" ] || [ "$TTY_GROUP" = "root" ]; then
        echo -e "  ${GREEN}✅ Grupo correcto: $TTY_GROUP${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Grupo: $TTY_GROUP (debería ser dialout)${NC}"
    fi
    
    # Verificar si el usuario está en dialout
    if groups | grep -q "dialout"; then
        echo -e "  ${GREEN}✅ Tu usuario pertenece al grupo dialout${NC}"
    else
        echo -e "  ${RED}❌ No estás en el grupo dialout${NC}"
        echo "     Ejecuta: sudo usermod -a -G dialout ubuntu"
        BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
    fi
else
    echo -e "  ${RED}❌ No se encontró puerto ttyUSB para el LiDAR${NC}"
fi

# Enlace /dev/rplidar
if [ -L /dev/rplidar ]; then
    RPLIDAR_LINK=$(readlink -f /dev/rplidar)
    echo -e "  ${GREEN}✅ /dev/rplidar → $RPLIDAR_LINK${NC}"
else
    echo -e "  ${YELLOW}⚠️  /dev/rplidar no existe${NC}"
fi
echo ""

# -----------------------------------------------------------
# 3. Velocidad de negociación USB
# -----------------------------------------------------------
echo -e "${CYAN}[3/8] Velocidad de negociación USB${NC}"
echo "----------------------------------------------"

USB_SPEED=$(lsusb -t 2>/dev/null | grep -A1 "cp210x" | grep -oP '\d+M' | head -1)

if [ -n "$USB_SPEED" ]; then
    case "$USB_SPEED" in
        12M)
            echo -e "  ${RED}❌ Velocidad: 12 Mbps (USB Full Speed)${NC}"
            echo "     Esto NO es un fallo del puerto, es lo que negocia el chip CP210x."
            echo "     La velocidad es suficiente para los datos del LiDAR (~115 kbps)."
            echo "     El problema real es la corriente, no la velocidad."
            ;;
        480M)
            echo -e "  ${GREEN}✅ Velocidad: 480 Mbps (USB 2.0 Hi-Speed)${NC}" ;;
        5000M)
            echo -e "  ${GREEN}✅ Velocidad: 5000 Mbps (USB 3.0 SuperSpeed)${NC}" ;;
        *)
            echo -e "  ${YELLOW}⚠️  Velocidad: $USB_SPEED${NC}" ;;
    esac
else
    echo -e "  ${YELLOW}⚠️  No se pudo determinar la velocidad USB${NC}"
fi
echo ""

# -----------------------------------------------------------
# 4. Corriente solicitada por el dispositivo
# -----------------------------------------------------------
echo -e "${CYAN}[4/8] Corriente solicitada (bMaxPower)${NC}"
echo "----------------------------------------------"

MAXPOWER=$(sudo lsusb -v -d 10c4:ea60 2>/dev/null | grep "MaxPower" | grep -oP '\d+')

if [ -n "$MAXPOWER" ]; then
    echo -e "  ${RED}❌ Corriente solicitada: ${MAXPOWER}mA${NC}"
    echo "     El chip CP210x solo pide ${MAXPOWER}mA."
    echo "     La Pi respeta este límite → el LiDAR no recibe suficiente corriente."
    echo ""
    echo -e "  ${YELLOW}📌 Esta es la CAUSA RAÍZ del problema.${NC}"
    echo "     El LiDAR necesita ~350-400mA estables y ~600mA de pico al arrancar."
    BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
else
    echo -e "  ${YELLOW}⚠️  No se pudo leer MaxPower${NC}"
fi

# Verificar si es Bus Powered o Self Powered
POWER_TYPE=$(sudo lsusb -v -d 10c4:ea60 2>/dev/null | grep "Bus Powered" | head -1)
if [ -n "$POWER_TYPE" ]; then
    echo -e "  ${YELLOW}⚠️  Tipo de alimentación: Bus Powered (toma corriente del bus USB)${NC}"
fi
echo ""

# -----------------------------------------------------------
# 5. Errores USB en el kernel relacionados con este dispositivo
# -----------------------------------------------------------
echo -e "${CYAN}[5/8] Errores USB del kernel (filtrados CP210x/USB)${NC}"
echo "----------------------------------------------"

DMESG_USB=$(dmesg 2>/dev/null | grep -iE "cp210x|ttyUSB|usb.*$BUS.*$DEV|over.current|power budget")

if [ -z "$DMESG_USB" ]; then
    echo -e "  ${GREEN}✅ Sin errores del kernel relacionados con el LiDAR${NC}"
else
    echo -e "  ${RED}❌ Se encontraron mensajes relevantes:${NC}"
    echo "$DMESG_USB" | tail -10 | sed 's/^/     /'
    BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
fi
echo ""

# -----------------------------------------------------------
# 6. Procesos que usan el puerto serie
# -----------------------------------------------------------
echo -e "${CYAN}[6/8] Procesos bloqueando el puerto serie${NC}"
echo "----------------------------------------------"

if [ -n "$TTY_USB" ]; then
    LSOF_OUT=$(sudo lsof /dev/$TTY_USB 2>/dev/null)
    if [ -n "$LSOF_OUT" ]; then
        echo -e "  ${YELLOW}⚠️  Hay procesos usando el puerto:${NC}"
        echo "$LSOF_OUT" | head -10 | sed 's/^/     /'
        BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
    else
        echo -e "  ${GREEN}✅ Puerto libre (sin procesos bloqueándolo)${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  No se encontró puerto ttyUSB para verificar${NC}"
fi
echo ""

# -----------------------------------------------------------
# 7. Configuración del puerto serie (stty)
# -----------------------------------------------------------
echo -e "${CYAN}[7/8] Configuración actual del puerto serie${NC}"
echo "----------------------------------------------"

if [ -n "$TTY_USB" ]; then
    STTY_OUT=$(sudo stty -F /dev/$TTY_USB -a 2>/dev/null)
    if [ -n "$STTY_OUT" ]; then
        echo "$STTY_OUT" | grep -E "speed|icanon|echo|min|time" | sed 's/^/  /'
        
        # Verificar modo canónico
        if echo "$STTY_OUT" | grep -q "\-icanon"; then
            echo -e "  ${GREEN}✅ Puerto en modo raw (-icanon): correcto para datos binarios${NC}"
        else
            echo -e "  ${RED}❌ Puerto en modo canónico (icanon): bloqueará datos binarios${NC}"
            echo "     Ejecuta: sudo stty -F /dev/$TTY_USB raw 115200 -echo"
            BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
        fi
    else
        echo -e "  ${RED}❌ No se pudo leer la configuración del puerto${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  No se encontró puerto ttyUSB para verificar${NC}"
fi
echo ""

# -----------------------------------------------------------
# 8. Prueba rápida de datos (timeout de 2 segundos)
# -----------------------------------------------------------
echo -e "${CYAN}[8/8] Prueba de recepción de datos (2 segundos)${NC}"
echo "----------------------------------------------"

if [ -n "$TTY_USB" ]; then
    # Configurar puerto antes de probar
    sudo stty -F /dev/$TTY_USB raw 115200 -echo -echoe -echok 2>/dev/null
    
    echo -e "  ${YELLOW}Escuchando en /dev/$TTY_USB por 2 segundos...${NC}"
    echo "  (Asegúrate de que el LiDAR esté girando)"
    echo ""
    
    DATA=$(timeout 2 cat /dev/$TTY_USB 2>/dev/null | od -x | head -5)
    
    if [ -z "$DATA" ] || [ "$DATA" = "0000000" ]; then
        echo -e "  ${RED}❌ No se recibieron datos${NC}"
        echo ""
        echo "  Posibles causas:"
        echo "    1. El motor del LiDAR no está girando (no hay suficiente corriente)"
        echo "    2. El puerto está en modo canónico (ver punto 7)"
        echo "    3. El cable USB solo carga, no transmite datos"
        echo "    4. El LiDAR necesita ser inicializado (el nodo ROS lo hace)"
        BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
    else
        echo -e "  ${GREEN}✅ ¡DATOS RECIBIDOS!${NC}"
        echo "     Primeros bytes:"
        echo "$DATA" | sed 's/^/     /'
    fi
else
    echo -e "  ${RED}❌ No se encontró puerto ttyUSB para probar${NC}"
    BLOCKERS_FOUND=$((BLOCKERS_FOUND + 1))
fi
echo ""

# -----------------------------------------------------------
# Resumen final
# -----------------------------------------------------------
echo "╔══════════════════════════════════════════════╗"
echo "║   RESUMEN FINAL                           ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

if [ $CP210X_FOUND -eq 0 ]; then
    echo -e "  ${RED}❌ El adaptador CP210x no fue detectado.${NC}"
    echo "     Conecta el LiDAR por USB e intenta de nuevo."
elif [ $BLOCKERS_FOUND -eq 0 ]; then
    echo -e "  ${GREEN}✅ No se detectaron bloqueos ni limitaciones en la comunicación USB.${NC}"
    echo ""
    echo "  Si el LiDAR no envía datos, la causa es únicamente la corriente insuficiente"
    echo "  (el chip CP210x negocia solo 100mA). La comunicación USB en sí funciona."
    echo ""
    echo -e "  ${YELLOW}Solución definitiva:${NC}"
    echo "    Alimenta el LiDAR externamente (DFR0205 5V + batería 12V)"
    echo "    y conecta solo los datos por GPIO (/dev/rlidar_gpio)."
else
    echo -e "  ${RED}❌ Se encontraron $BLOCKERS_FOUND problema(s) de comunicación USB.${NC}"
    echo ""
    echo "  Revisa los mensajes marcados en rojo arriba."
    echo "  La causa más probable es la corriente insuficiente (100mA)."
fi

echo ""
echo "  Puerto USB detectado:  ${TTY_USB:-no encontrado}"
echo "  Corriente solicitada:  ${MAXPOWER:-?}mA"
echo "  Velocidad negociada:   ${USB_SPEED:-?}"
echo "  Errores kernel:        ${DMESG_USB:-ninguno}"
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   DIAGNÓSTICO COMPLETADO                  ║"
echo "╚══════════════════════════════════════════════╝"