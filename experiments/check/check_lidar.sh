#!/bin/bash

echo "========================================="
echo "  DIAGNÓSTICO RÁPIDO RPLIDAR A1"
echo "========================================="
echo ""
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # Sin color
echo -n "1. Dispositivo /dev/rplidar: "
if [ -L /dev/rplidar ]; then
    TARGET=$(readlink -f /dev/rplidar)
    echo -e "${GREEN}Existe → $TARGET${NC}"
else
    echo -e "${RED}NO EXISTE${NC}"
    echo "   Verifica la conexión USB"
    exit 1
fi
echo -n "2. Puerto serial: "
if [ -c "$TARGET" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}NO es un dispositivo válido${NC}"
    exit 1
fi
echo -n "3. Velocidad USB: "
SPEED=$(lsusb -t 2>/dev/null | grep "cp210x" | grep -oP '\d+M' | head -1)
if [ -n "$SPEED" ]; then
    if [ "$SPEED" = "480M" ] || [ "$SPEED" = "5000M" ]; then
        echo -e "${GREEN}$SPEED (correcto)${NC}"
    else
        echo -e "${RED}$SPEED (MUY BAJO - necesita 480M o más)${NC}"
        echo "   Conecta el LiDAR directamente a un puerto USB 3.0 (azul) de la Pi"
    fi
else
    echo -e "${YELLOW}No se pudo determinar${NC}"
fi
echo -n "4. Potencia disponible: "
MAX_POWER=$(sudo lsusb -v -d 10c4:ea60 2>/dev/null | grep "MaxPower" | grep -oP '\d+')
POWER_TYPE=$(sudo lsusb -v -d 10c4:ea60 2>/dev/null | grep "Bus Powered" | head -1)
if [ -n "$MAX_POWER" ]; then
    if [ "$MAX_POWER" -ge 500 ] 2>/dev/null; then
        echo -e "${GREEN}${MAX_POWER}mA (suficiente)${NC}"
    else
        echo -e "${RED}${MAX_POWER}mA (INSUFICIENTE - necesita 500mA+)${NC}"
        if echo "$POWER_TYPE" | grep -q "Bus Powered"; then
            echo "   El LiDAR está alimentado por el bus (limitado)"
            echo "   SOLUCIÓN: Conecta directo a la Pi (sin hub) o usa fuente externa"
        fi
    fi
else
    echo -e "${YELLOW}No se pudo determinar${NC}"
fi
echo -n "5. Configurando puerto serial: "
sudo stty -F /dev/rplidar raw 115200 -echo -echoe -echok 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}ERROR${NC}"
    exit 1
fi
echo -n "6. Probando recepción de datos (2 segundos): "
DATA=""
DATA=$(timeout 2 cat /dev/rplidar 2>/dev/null | od -x 2>/dev/null | head -3)

if [ -z "$DATA" ] || [ "$DATA" = "0000000" ] || [ "$DATA" = "0000000 " ]; then
    echo -e "${RED}NO ENVÍA DATOS${NC}"
    echo ""
    echo "   Posibles causas:"
    echo "   • El LiDAR no está girando (¿escuchas el motor?)"
    echo "   • Alimentación insuficiente (necesita 5V/1A para arrancar)"
    echo "   • Cable USB defectuoso"
    echo "   • Puerto serial mal configurado"
    echo ""
    echo "   ACCIONES A SEGUIR (en orden):"
    echo "   1. Conecta el LiDAR DIRECTAMENTE a la Pi (sin hub)"
    echo "      └─ Usa un puerto USB 3.0 (azul)"
    echo "   2. Verifica que el LiDAR esté GIRANDO"
    echo "      └─ Debes escuchar el motor al conectar"
    echo "   3. Prueba con otro cable USB (más corto/grueso)"
    echo "   4. Si aún falla, ejecuta:"
    echo "      └─ sudo cat /dev/rplidar | od -x (Ctrl+C después de 2 seg)"
    echo ""
    echo "   ¿Motor gira pero no hay datos?"
    echo "   → Puede ser problema del firmware del LiDAR"
    echo "   → Probar: github.com/Slamtec/rplidar_sdk"
else
    echo -e "${GREEN}¡ENVÍA DATOS! ✓${NC}"
    echo "   Primeros bytes:"
    echo "$DATA" | sed 's/^/   /'
fi
echo -n "7. Procesos usando el puerto: "
LSOF_OUT=$(sudo lsof /dev/rplidar 2>/dev/null | head -5)
if [ -n "$LSOF_OUT" ]; then
    echo -e "${GREEN}En uso${NC}"
    echo "$LSOF_OUT" | sed 's/^/   /'
else
    echo -e "${YELLOW}Ninguno (el puerto está libre)${NC}"
fi
echo -n "8. Nodo RPLidar en ROS: "
if ros2 node list 2>/dev/null | grep -q "rplidar_node"; then
    echo -e "${GREEN}Ejecutándose${NC}"
else
    echo -e "${YELLOW}No encontrado${NC}"
fi

echo -n "9. Nodo scan_filter en ROS: "
if ros2 node list 2>/dev/null | grep -q "scan_filter"; then
    echo -e "${GREEN}Ejecutándose${NC}"
else
    echo -e "${YELLOW}No encontrado${NC}"
fi
echo -n "10. Tópico /scan_raw: "
if ros2 topic list 2>/dev/null | grep -q "/scan_raw"; then
    TOPIC_INFO=$(ros2 topic info /scan_raw 2>/dev/null)
    PUB_COUNT=$(echo "$TOPIC_INFO" | grep "Publisher count:" | awk '{print $3}')
    if [ "$PUB_COUNT" -gt 0 ]; then
        echo -e "${GREEN}Publicando ($PUB_COUNT publisher)${NC}"
        HZ_INFO=$(timeout 3 ros2 topic hz /scan_raw 2>/dev/null | tail -1)
        if [ -n "$HZ_INFO" ]; then
            echo "   Frecuencia: $HZ_INFO"
        fi
    else
        echo -e "${RED}Sin publisher${NC}"
    fi
else
    echo -e "${RED}No existe${NC}"
fi

echo -n "11. Tópico /scan: "
if ros2 topic list 2>/dev/null | grep -q "^/scan$"; then
    TOPIC_INFO=$(ros2 topic info /scan 2>/dev/null)
    PUB_COUNT=$(echo "$TOPIC_INFO" | grep "Publisher count:" | awk '{print $3}')
    if [ "$PUB_COUNT" -gt 0 ]; then
        echo -e "${GREEN}Publicando ($PUB_COUNT publisher)${NC}"
    else
        echo -e "${RED}Sin publisher${NC}"
    fi
else
    echo -e "${RED}No existe${NC}"
fi
echo -n "12. Contenido de /scan: "
SCAN_CONTENT=$(timeout 2 ros2 topic echo /scan --csv 2>/dev/null | head -3)
if echo "$SCAN_CONTENT" | grep -q "ranges"; then
    echo -e "${GREEN}Contiene datos de ranges ✓${NC}"
    echo "$SCAN_CONTENT" | head -2 | sed 's/^/   /'
else
    echo -e "${RED}Sin datos de ranges o tópico sin publicar${NC}"
fi
echo ""
echo "========================================="
echo "  RESUMEN Y PRÓXIMOS PASOS"
echo "========================================="
echo ""
echo "Para que el LiDAR funcione correctamente:"
echo "  ✓ /dev/rplidar debe existir"
echo "  ✓ Velocidad USB: 480M o 5000M"
echo "  ✓ Potencia: 500mA o más"
echo "  ✓ Debe enviar datos (test 6)"
echo "  ✓ Nodo rplidar_node ejecutándose"
echo "  ✓ Tópico /scan_raw con publisher"
echo "  ✓ Tópico /scan con datos de ranges"
echo ""
echo "PROBLEMA PRINCIPAL ENCONTRADO:"
echo "  El LiDAR necesita 500mA+ para arrancar"
echo "  El hub solo proporciona 100mA"
echo ""
echo "SOLUCIÓN INMEDIATA:"
echo "  Conecta el LiDAR DIRECTAMENTE a la Pi"
echo "  Usa un puerto USB 3.0 (azul)"