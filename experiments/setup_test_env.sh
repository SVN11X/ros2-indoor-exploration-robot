#!/usr/bin/env bash

set -e

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
RED="\033[0;31m"
NC="\033[0m"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Setup entorno de pruebas /test        ${NC}"
echo -e "${GREEN}========================================${NC}"
DISTRO=$(lsb_release -rs 2>/dev/null || echo "unknown")
if [[ "$DISTRO" != "20.04" ]]; then
    echo -e "${YELLOW}AVISO: Se detectó Ubuntu $DISTRO. Script probado en 20.04.${NC}"
fi
INSIDE_VENV=0
if [[ -n "$VIRTUAL_ENV" ]]; then
    INSIDE_VENV=1
    VENV_PATH="$VIRTUAL_ENV"
    echo -e "${YELLOW}AVISO: Se detectó un virtualenv activo: $VENV_PATH${NC}"
    echo -e "${YELLOW}       Los paquetes apt y ROS2 se instalan en el sistema.${NC}"
    echo -e "${YELLOW}       Las librerías pip se instalarán DENTRO del venv.${NC}"
    deactivate 2>/dev/null || true
fi
echo -e "\n${YELLOW}[1/4] Actualizando apt...${NC}"
sudo apt-get update -qq
echo -e "\n${YELLOW}[2/4] Instalando dependencias del sistema...${NC}"
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-tk \
    libpng-dev \
    libfreetype6-dev \
    libblas-dev \
    liblapack-dev \
    gfortran
echo -e "\n${YELLOW}[3/4] Instalando paquetes ROS2 Python (apt)...${NC}"

ROS2_PKGS=(
    ros-foxy-rclpy
    ros-foxy-geometry-msgs
    ros-foxy-nav-msgs
    ros-foxy-sensor-msgs
    ros-foxy-rosbag2
    ros-foxy-rosbag2-storage-default-plugins
    ros-foxy-ros2bag
    ros-foxy-rosbag2-storage-mcap
)

for pkg in "${ROS2_PKGS[@]}"; do
    if apt-cache show "$pkg" &>/dev/null; then
        sudo apt-get install -y "$pkg"
        echo -e "  ${GREEN}✓ $pkg${NC}"
    else
        echo -e "  ${YELLOW}~ $pkg  (no disponible, se omite)${NC}"
    fi
done
echo -e "\n${YELLOW}[4/4] Instalando librerías Python (pip)...${NC}"
if [[ $INSIDE_VENV -eq 1 ]]; then
    echo -e "${YELLOW}       Reactivando virtualenv para pip...${NC}"
    source "$VENV_PATH/bin/activate"
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"

if [[ ! -f "$REQUIREMENTS" ]]; then
    echo -e "${RED}ERROR: no se encuentra requirements.txt en $SCRIPT_DIR${NC}"
    exit 1
fi

pip3 install --upgrade pip --quiet
pip3 install -r "$REQUIREMENTS"
echo -e "\n${GREEN}Verificando instalación...${NC}"
python3 - <<'PYCHECK'
import importlib, sys
libs = {
    "numpy":      "numpy",
    "matplotlib": "matplotlib",
    "pandas":     "pandas",
    "scipy":      "scipy",
    "serial":     "pyserial",
}
ok = True
for mod, name in libs.items():
    try:
        m = importlib.import_module(mod)
        ver = getattr(m, "__version__", "?")
        print(f"  \033[92m✓\033[0m  {name:<12} {ver}")
    except ImportError:
        print(f"  \033[91m✗\033[0m  {name:<12} NO INSTALADO", file=sys.stderr)
        ok = False
try:
    import rclpy
    print(f"  \033[92m✓\033[0m  rclpy        (ROS2 sistema)")
except ImportError:
    print("  \033[93m~\033[0m  rclpy        (ROS2 — recuerda: source /opt/ros/foxy/setup.bash)")
if not ok:
    sys.exit(1)
PYCHECK

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}  Entorno listo.                         ${NC}"
echo -e "${GREEN}  Ejecuta antes de usar los scripts:     ${NC}"
echo -e "${GREEN}  source /opt/ros/foxy/setup.bash        ${NC}"
if [[ $INSIDE_VENV -eq 1 ]]; then
echo -e "${GREEN}  source $VENV_PATH/bin/activate   ${NC}"
fi
echo -e "${GREEN}========================================${NC}"