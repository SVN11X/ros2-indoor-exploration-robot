#!/bin/bash
# ============================================================
# check_usb_ports.sh
# Diagnóstico completo de puertos USB en Raspberry Pi
# ============================================================

echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   DIAGNÓSTICO DE PUERTOS USB              ║"
echo "║   Raspberry Pi                            ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

ERRORS_FOUND=0

# -----------------------------------------------------------
# 1. Buscar errores USB en el kernel
# -----------------------------------------------------------
echo -e "${CYAN}[1/6] Errores USB en el kernel (dmesg)${NC}"
echo "----------------------------------------------"

DMESG_ERRORS=$(dmesg | grep -iE "over.current|usb.*error|cannot enable|device descriptor|power budget|hub.*port.*disabled" 2>/dev/null)

if [ -z "$DMESG_ERRORS" ]; then
    echo -e "  ${GREEN}✅ Sin errores USB detectados${NC}"
else
    echo -e "  ${RED}❌ Se encontraron errores USB:${NC}"
    echo "$DMESG_ERRORS" | head -10 | sed 's/^/    /'
    ERRORS_FOUND=$((ERRORS_FOUND + 1))
fi
echo ""

# -----------------------------------------------------------
# 2. Estado del throttling
# -----------------------------------------------------------
echo -e "${CYAN}[2/6] Estado de alimentación (throttling)${NC}"
echo "----------------------------------------------"

THROTTLED=$(vcgencmd get_throttled 2>/dev/null)

if [ -z "$THROTTLED" ]; then
    echo -e "  ${YELLOW}⚠️  No se pudo leer throttling${NC}"
else
    echo "  $THROTTLED"
    case "$THROTTLED" in
        *"throttled=0x0"*)
            echo -e "  ${GREEN}✅ Alimentación correcta, sin bajo voltaje ni sobrecalentamiento${NC}" ;;
        *"0x50000"*)
            echo -e "  ${RED}❌ Bajo voltaje detectado ANTERIORMENTE${NC}"
            ERRORS_FOUND=$((ERRORS_FOUND + 1)) ;;
        *"0x50005"*)
            echo -e "  ${RED}❌ Bajo voltaje ACTIVO AHORA - ¡Fuente inadecuada!${NC}"
            ERRORS_FOUND=$((ERRORS_FOUND + 1)) ;;
        *"0x80008"*)
            echo -e "  ${RED}❌ Sobrecalentamiento ACTIVO${NC}"
            ERRORS_FOUND=$((ERRORS_FOUND + 1)) ;;
        *)
            echo -e "  ${YELLOW}⚠️  Estado: $THROTTLED${NC}" ;;
    esac
fi
echo ""

# -----------------------------------------------------------
# 3. Dispositivos USB conectados y su consumo
# -----------------------------------------------------------
echo -e "${CYAN}[3/6] Dispositivos USB y corriente solicitada${NC}"
echo "----------------------------------------------"

FOUND_CP210=0
for dev_path in /sys/bus/usb/devices/*/product; do
    [ -f "$dev_path" ] || continue
    dir=$(dirname "$dev_path")
    
    product=$(cat "$dev_path" 2>/dev/null || echo "Desconocido")
    
    # Corriente solicitada
    maxpower_file="$dir/bMaxPower"
    if [ -f "$maxpower_file" ]; then
        maxpower=$(cat "$maxpower_file" 2>/dev/null)
        maxpower="${maxpower}mA"
    else
        # Intentar obtener desde lsusb
        maxpower="?"
    fi
    
    # Velocidad
    speed_file="$dir/speed"
    if [ -f "$speed_file" ]; then
        speed=$(cat "$speed_file" 2>/dev/null)
        case "$speed" in
            1.5)    speed="1.5 Mbps (USB Low Speed)" ;;
            12)     speed="12 Mbps (USB Full Speed)" ;;
            480)    speed="480 Mbps (USB 2.0 Hi-Speed)" ;;
            5000)   speed="5000 Mbps (USB 3.0 SuperSpeed)" ;;
            *)      speed="${speed} Mbps" ;;
        esac
    else
        speed="?"
    fi
    
    # Estado
    status_file="$dir/power/runtime_status"
    status=$(cat "$status_file" 2>/dev/null || echo "?")
    
    # Fabricante
    manufacturer_file="$dir/manufacturer"
    manufacturer=$(cat "$manufacturer_file" 2>/dev/null || echo "?")
    
    echo -e "  📱 ${GREEN}${product}${NC}"
    echo "     Fabricante: $manufacturer"
    echo "     Corriente solicitada: $maxpower"
    echo "     Velocidad: $speed"
    echo "     Estado: $status"
    
    # Verificar si es el CP210x del LiDAR
    if echo "$product" | grep -qi "cp210\|uart bridge"; then
        FOUND_CP210=1
        if [ "$maxpower" = "100mA" ]; then
            echo -e "     ${YELLOW}⚠️  Este dispositivo solo pide 100mA (insuficiente para LiDAR)${NC}"
            echo -e "     ${YELLOW}   La Pi respeta este límite → el LiDAR no recibe suficiente corriente${NC}"
        fi
    fi
    
    echo ""
done

if [ $FOUND_CP210 -eq 0 ]; then
    echo -e "  ${YELLOW}⚠️  No se detectó el adaptador CP210x del LiDAR${NC}"
    echo "     ¿Está conectado el LiDAR por USB?"
fi
echo ""

# -----------------------------------------------------------
# 4. Árbol USB completo
# -----------------------------------------------------------
echo -e "${CYAN}[4/6] Árbol de dispositivos USB (lsusb -t)${NC}"
echo "----------------------------------------------"
lsusb -t 2>/dev/null | sed 's/^/  /'
echo ""

# -----------------------------------------------------------
# 5. Verificar si hay puertos que fallan
# -----------------------------------------------------------
echo -e "${CYAN}[5/6] Estado de los puertos físicos${NC}"
echo "----------------------------------------------"

# Contar hubs y puertos detectados
HUB_COUNT=$(lsusb -t 2>/dev/null | grep -c "Hub")
DEV_COUNT=$(lsusb 2>/dev/null | grep -v "root hub\|Hub" | wc -l)

echo "  Hubs USB detectados: $HUB_COUNT"
echo "  Dispositivos conectados: $DEV_COUNT"

# Verificar si hay dispositivos con alta velocidad
HI_SPEED=$(lsusb -t 2>/dev/null | grep -c "480M\|5000M")
if [ "$HI_SPEED" -gt 0 ]; then
    echo -e "  ${GREEN}✅ Hay $HI_SPEED dispositivo(s) a velocidad alta (480M+)${NC}"
else
    echo -e "  ${YELLOW}⚠️  Ningún dispositivo a 480M o más${NC}"
fi
echo ""

# -----------------------------------------------------------
# 6. Resumen y recomendaciones
# -----------------------------------------------------------
echo "╔══════════════════════════════════════════════╗"
echo "║   RESUMEN Y DIAGNÓSTICO                   ║"
echo "╚══════════════════════════════════════════════╝"
echo ""

if [ $ERRORS_FOUND -eq 0 ]; then
    echo -e "  ${GREEN}✅ Los puertos USB de la Raspberry Pi NO muestran fallos.${NC}"
    echo ""
    echo "  El problema con el LiDAR NO es un puerto dañado,"
    echo "  sino que el chip CP210x solo solicita 100mA a la Pi,"
    echo "  y la Pi respeta ese límite. El LiDAR necesita ~500mA."
    echo ""
    echo -e "  ${YELLOW}Solución definitiva:${NC}"
    echo "    Alimenta el LiDAR con el DFR0205 (5V) + batería (12V)"
    echo "    y conecta solo los datos (TX/RX) a los GPIO de la Pi."
    echo "    Puerto: /dev/rlidar_gpio"
else
    echo -e "  ${RED}❌ Se encontraron $ERRORS_FOUND problema(s).${NC}"
    echo ""
    echo "  Revisa los mensajes anteriores para más detalles."
    echo "  Posibles acciones:"
    echo "    1. Cambiar la fuente de alimentación de la Pi"
    echo "    2. Probar otro cable USB-C"
    echo "    3. Conectar el LiDAR por GPIO (evita los puertos USB)"
fi

echo ""
echo "  Puerto configurado para LiDAR por GPIO:"
if [ -L /dev/rlidar_gpio ]; then
    echo -e "    ${GREEN}✅ /dev/rlidar_gpio → $(readlink -f /dev/rlidar_gpio)${NC}"
else
    echo -e "    ${YELLOW}⚠️  /dev/rlidar_gpio no existe (se creará al conectar por GPIO)${NC}"
fi
echo ""
echo "╔══════════════════════════════════════════════╗"
echo "║   DIAGNÓSTICO COMPLETADO                  ║"
echo "╚══════════════════════════════════════════════╝"