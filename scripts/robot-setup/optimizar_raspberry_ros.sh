#!/bin/bash
# ============================================================
# Script: optimizar_raspberry_ros.sh
# Descripción: Optimiza Raspberry Pi con Ubuntu Server para ROS 2
#              sin perjudicar servicios esenciales (SSH, WiFi, ROS)
# ============================================================

set -e  # Detener si hay error

echo ""
echo "========================================="
echo "  OPTIMIZACIÓN RASPBERRY PI PARA ROS 2"
echo "========================================="
echo ""

# Verificar que se ejecuta como usuario normal (no root directamente)
if [ "$EUID" -eq 0 ]; then
    echo "ERROR: No ejecutes este script como root."
    echo "       Ejecútalo con tu usuario normal (ubuntu)."
    exit 1
fi

echo "Este script desactivará servicios innecesarios"
echo "y liberará recursos para ROS 2."
echo ""
echo "Servicios que se MANTENDRÁN:"
echo "  ✅ SSH (acceso remoto)"
echo "  ✅ WiFi (conexión de red)"
echo "  ✅ systemd-udevd (gestión de hardware)"
echo "  ✅ cron (tareas programadas)"
echo "  ✅ Todos los paquetes de ROS 2"
echo ""
read -p "¿Continuar? [S/n]: " -r RESP
if [[ "$RESP" =~ ^[nN] ]]; then
    echo "Cancelado."
    exit 0
fi

echo ""
echo "[1/7] Desactivando entorno gráfico (GUI)..."
sudo systemctl stop gdm3 2>/dev/null || true
sudo systemctl disable gdm3 2>/dev/null || true
sudo systemctl stop lightdm 2>/dev/null || true
sudo systemctl disable lightdm 2>/dev/null || true
sudo systemctl set-default multi-user.target 2>/dev/null || true
echo "  ✓ GUI desactivada"

echo ""
echo "[2/7] Desactivando Bluetooth..."
sudo systemctl stop bluetooth 2>/dev/null || true
sudo systemctl disable bluetooth 2>/dev/null || true
sudo systemctl mask bluetooth 2>/dev/null || true
echo "  ✓ Bluetooth desactivado"

echo ""
echo "[3/7] Desactivando audio..."
sudo systemctl stop alsa-restore 2>/dev/null || true
sudo systemctl disable alsa-restore 2>/dev/null || true
sudo systemctl stop pulseaudio 2>/dev/null || true
sudo systemctl disable pulseaudio 2>/dev/null || true
sudo systemctl stop pipewire 2>/dev/null || true
sudo systemctl disable pipewire 2>/dev/null || true
echo "  ✓ Audio desactivado"

echo ""
echo "[4/7] Eliminando impresión (CUPS)..."
sudo apt purge --auto-remove -y cups 2>/dev/null || true
echo "  ✓ Impresión eliminada"

echo ""
echo "[5/7] Eliminando snaps (paquetes autocontenidos)..."
if dpkg -l | grep -q snapd; then
    sudo apt purge --auto-remove -y snapd 2>/dev/null || true
    sudo rm -rf /var/cache/snapd /snap 2>/dev/null || true
    echo "  ✓ Snapd eliminado"
else
    echo "  ✓ Snapd ya estaba eliminado"
fi

echo ""
echo "[6/7] Desactivando servicios innecesarios..."

SERVICIOS=(
    ModemManager
    kerneloops
    avahi-daemon
    apport
    apport-autoreport
    whoopsie
    accounts-daemon
    polkit
    rtkit-daemon
    upower
    colord
)

for srv in "${SERVICIOS[@]}"; do
    if systemctl list-units --all 2>/dev/null | grep -q "$srv"; then
        sudo systemctl stop "$srv" 2>/dev/null || true
        sudo systemctl disable "$srv" 2>/dev/null || true
        echo "  ✓ $srv desactivado"
    fi
done

echo ""
echo "[7/7] Limpieza final..."

# Eliminar paquetes huérfanos
sudo apt autoremove -y 2>/dev/null || true
sudo apt autoclean 2>/dev/null || true

# Desactivar WiFi power save para mejor latencia SSH
if iwconfig wlan0 2>/dev/null | grep -q "Power Management"; then
    sudo iwconfig wlan0 power off 2>/dev/null || true
    # Hacerlo permanente
    if ! grep -q "iwconfig wlan0 power off" /etc/rc.local 2>/dev/null; then
        echo "iwconfig wlan0 power off" | sudo tee -a /etc/rc.local > /dev/null
        sudo chmod +x /etc/rc.local
    fi
    echo "  ✓ WiFi Power Save desactivado"
fi

echo ""
echo "========================================="
echo "  OPTIMIZACIÓN COMPLETADA"
echo "========================================="
echo ""

# Mostrar estadísticas finales
RAM_FREE=$(free -h | awk '/Mem:/ {print $4}')
DISK_USED=$(df -h / | awk 'NR==2 {print $5}')
SERVICES_ACTIVE=$(systemctl list-units --type=service --state=running | wc -l)

echo "  RAM libre:         $RAM_FREE"
echo "  Disco usado:       $DISK_USED"
echo "  Servicios activos: $SERVICES_ACTIVE"
echo ""
echo "  Servicios MANTENIDOS:"
echo "    ✅ SSH (acceso remoto)"
echo "    ✅ WiFi (conexión de red)"
echo "    ✅ systemd-udevd (hardware)"
echo "    ✅ cron (tareas programadas)"
echo "    ✅ ROS 2 y dependencias"
echo ""
echo "  Para aplicar todos los cambios:"
echo "    sudo reboot"
echo ""