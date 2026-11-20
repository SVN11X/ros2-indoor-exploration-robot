#!/bin/bash
echo "=== DIAGNÓSTICO RPLIDAR ==="
echo ""

echo "1. Dispositivo:"
ls -la /dev/rplidar /dev/ttyUSB* 2>/dev/null
echo ""

echo "2. Procesos relacionados:"
ps aux | grep -E "rplidar|scan" | grep -v grep
echo ""

echo "3. Puerto serial (5 segundos):"
timeout 5 cat /dev/rplidar | od -x | head -10
echo ""

echo "4. Estado del LiDAR:"
if [ -e /dev/rplidar ]; then
    stty -F /dev/rplidar -a
fi
echo ""

echo "5. Mensajes recientes del kernel:"
dmesg | tail -10 | grep -i usb
echo ""

echo "6. Información USB:"
lsusb | grep -i "10c4:ea60"  # ID del RPLidar
echo ""

echo "7. Estado del motor:"
echo "  ¿El LiDAR está girando? (S/N)"
read -r respuesta
echo "  Respuesta: $respuesta"