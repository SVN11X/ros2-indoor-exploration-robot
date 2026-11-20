#!/bin/bash
# optimizar_arranque.sh - Acelera el inicio de la Raspberry Pi

echo "=== OPTIMIZANDO ARRANQUE ==="

# 1. Desactivar fstrim (solo útil para SSD, no para SD)
sudo systemctl disable fstrim.service 2>/dev/null
sudo systemctl disable fstrim.timer 2>/dev/null
echo "✓ fstrim desactivado"

# 2. Desactivar actualizaciones de firmware
sudo systemctl disable fwupd-refresh.service 2>/dev/null
sudo systemctl disable fwupd.service 2>/dev/null
sudo systemctl mask fwupd-refresh.service 2>/dev/null
sudo systemctl mask fwupd.service 2>/dev/null
echo "✓ fwupd desactivado"

# 3. Desactivar actualizaciones automáticas
sudo systemctl disable apt-daily.service 2>/dev/null
sudo systemctl disable apt-daily.timer 2>/dev/null
sudo systemctl disable apt-daily-upgrade.service 2>/dev/null
sudo systemctl disable apt-daily-upgrade.timer 2>/dev/null
sudo systemctl mask apt-daily.service 2>/dev/null
sudo systemctl mask apt-daily-upgrade.service 2>/dev/null
echo "✓ Actualizaciones automáticas desactivadas"

# 4. Desactivar mensaje del día
sudo systemctl disable motd-news.service 2>/dev/null
sudo systemctl mask motd-news.service 2>/dev/null
echo "✓ MOTD news desactivado"

# 5. Desactivar cloud-init (no estás en la nube)
sudo systemctl disable cloud-init-local.service 2>/dev/null
sudo systemctl disable cloud-init.service 2>/dev/null
sudo systemctl disable cloud-config.service 2>/dev/null
sudo systemctl disable cloud-final.service 2>/dev/null
echo "✓ Cloud-init desactivado"

# 6. Desactivar man-db (páginas de manual, puedes usar --help)
sudo systemctl disable man-db.service 2>/dev/null
sudo systemctl disable man-db.timer 2>/dev/null
sudo systemctl mask man-db.service 2>/dev/null
echo "✓ man-db desactivado"

# 7. Configurar NetworkManager para no esperar tanto
sudo systemctl disable NetworkManager-wait-online.service 2>/dev/null
echo "✓ NetworkManager-wait-online desactivado"

# 8. Desactivar servicios de logrotate (rotación de logs)
sudo systemctl disable logrotate.service 2>/dev/null
sudo systemctl disable logrotate.timer 2>/dev/null
echo "✓ logrotate desactivado"

echo ""
echo "=== ARRANQUE OPTIMIZADO ==="
echo "Tiempo estimado después del próximo reboot: ~12-15 segundos"
echo ""
echo "Ejecuta: sudo reboot"