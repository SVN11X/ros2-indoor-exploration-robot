#!/bin/bash
echo "╔═══════════════════════════════════╗"
echo "║   SALUD DE RASPBERRY PI         ║"
echo "╚═══════════════════════════════════╝"
echo ""

# Temperatura
TEMP=$(vcgencmd measure_temp | cut -d= -f2 | sed 's/..$//')
echo "🌡️  Temperatura:    ${TEMP}°C"
if (( $(echo "$TEMP > 80" | bc -l) )); then
    echo "   ❌ ¡PELIGRO! Temperatura muy alta"
elif (( $(echo "$TEMP > 70" | bc -l) )); then
    echo "   ⚠️  Temperatura elevada"
elif (( $(echo "$TEMP > 60" | bc -l) )); then
    echo "   ⚠️  Temperatura moderada"
else
    echo "   ✅ Temperatura normal"
fi
echo ""

# Voltaje
VOLT=$(vcgencmd measure_volts core | cut -d= -f2)
echo "⚡ Voltaje:         $VOLT"
echo ""

# Throttling
THROTTLED=$(vcgencmd get_throttled)
echo "📊 Estado throttling: $THROTTLED"
case "$THROTTLED" in
    *"0x0"*) echo "   ✅ Sin problemas detectados" ;;
    *"0x50000"*) echo "   ⚠️  Ha ocurrido bajo voltaje anteriormente" ;;
    *"0x50005"*) echo "   ❌ Bajo voltaje ACTIVO AHORA - Revisa la fuente" ;;
    *"0x80008"*) echo "   ❌ Sobrecalentamiento ACTIVO - ¡Enfriar ya!" ;;
esac
echo ""

# Frecuencia CPU
FREQ=$(vcgencmd measure_clock arm | cut -d= -f2)
echo "🚀 Frecuencia CPU:  $((FREQ / 1000000)) MHz"
echo ""

# RAM
echo "💾 Memoria RAM:"
free -h | awk 'NR==2{printf "   Total: %s  Usado: %s  Libre: %s  Disponible: %s\n", $2, $3, $4, $7}'
echo ""

# Disco
echo "💿 Almacenamiento:"
df -h / | awk 'NR==2{printf "   Total: %s  Usado: %s  Libre: %s  Uso: %s\n", $2, $3, $4, $5}'
echo ""

# Tiempo activo
echo "⏱️  Uptime: $(uptime -p)"
echo ""

# Procesos activos
PROCS=$(ps aux --no-headers | wc -l)
echo "📋 Procesos:        $PROCS"
echo ""

# Servicios activos
SRVS=$(systemctl list-units --type=service --state=running | wc -l)
echo "🔧 Servicios:       $SRVS"
echo ""

# Red
IP_WIFI=$(ip -4 addr show wlan0 2>/dev/null | grep -oP 'inet \K[\d.]+')
IP_ETH=$(ip -4 addr show eth0 2>/dev/null | grep -oP 'inet \K[\d.]+')
echo "🌐 Red:"
[ -n "$IP_WIFI" ] && echo "   WiFi: $IP_WIFI" || echo "   WiFi: No conectado"
[ -n "$IP_ETH" ] && echo "   Ethernet: $IP_ETH" || echo "   Ethernet: No conectado"
echo ""

echo "╔═══════════════════════════════════╗"
echo "║   DIAGNÓSTICO COMPLETADO         ║"
echo "╚═══════════════════════════════════╝"