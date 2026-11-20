#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# datos_estacion.sh
# Recolecta los datos de la estacion de trabajo que faltan en el Capitulo de
# Resultados (GE6): sistema operativo, kernel, procesador, memoria RAM,
# version de ROS 2 y version de Gazebo, mas las versiones de los paquetes
# clave de navegacion.
#
# Uso:   bash datos_estacion.sh
#        bash datos_estacion.sh > datos_estacion.txt
#
# No requiere permisos de root ni instalar nada.
# ---------------------------------------------------------------------------

set -u

linea() { printf '%s\n' "----------------------------------------------------------"; }
dato()  { printf '%-28s %s\n' "$1" "$2"; }

# Devuelve "no detectado" si el valor viene vacio
od() { local v="${1:-}"; [ -z "$v" ] && echo "no detectado" || echo "$v"; }

# ---------------------------------------------------------------------------
# 1. Sistema operativo
# ---------------------------------------------------------------------------
SO="$( . /etc/os-release 2>/dev/null && echo "$PRETTY_NAME" )"
KERNEL="$(uname -r)"
ARQ="$(uname -m)"

# ---------------------------------------------------------------------------
# 2. Procesador
# ---------------------------------------------------------------------------
CPU_MODELO="$(lscpu 2>/dev/null | sed -n 's/^Model name:[[:space:]]*//p' | head -1)"
[ -z "$CPU_MODELO" ] && CPU_MODELO="$(sed -n 's/^model name[[:space:]]*:[[:space:]]*//p' /proc/cpuinfo | head -1)"
CPU_NUCLEOS="$(lscpu 2>/dev/null | sed -n 's/^Core(s) per socket:[[:space:]]*//p' | head -1)"
CPU_SOCKETS="$(lscpu 2>/dev/null | sed -n 's/^Socket(s):[[:space:]]*//p' | head -1)"
CPU_HILOS="$(nproc 2>/dev/null)"
CPU_MAXMHZ="$(lscpu 2>/dev/null | sed -n 's/^CPU max MHz:[[:space:]]*//p' | head -1)"

if [ -n "$CPU_NUCLEOS" ] && [ -n "$CPU_SOCKETS" ]; then
  CPU_FISICOS=$(( CPU_NUCLEOS * CPU_SOCKETS ))
else
  CPU_FISICOS=""
fi

if [ -n "$CPU_MAXMHZ" ]; then
  CPU_GHZ="$(awk -v m="$CPU_MAXMHZ" 'BEGIN{printf "%.2f", m/1000}')"
else
  CPU_GHZ=""
fi

# ---------------------------------------------------------------------------
# 3. Memoria RAM
# ---------------------------------------------------------------------------
RAM_KB="$(sed -n 's/^MemTotal:[[:space:]]*\([0-9]*\).*/\1/p' /proc/meminfo)"
if [ -n "$RAM_KB" ]; then
  RAM_GIB="$(awk -v k="$RAM_KB" 'BEGIN{printf "%.1f", k/1048576}')"
  # Valor comercial redondeado (4, 8, 16, 32 GB)
  RAM_NOMINAL="$(awk -v k="$RAM_KB" 'BEGIN{
    g=k/1048576; n=4; while(n<g-0.5){n*=2} printf "%d", n}')"
else
  RAM_GIB=""; RAM_NOMINAL=""
fi

# ---------------------------------------------------------------------------
# 4. ROS 2
# ---------------------------------------------------------------------------
ROS_DISTRO_DET="${ROS_DISTRO:-}"
if [ -z "$ROS_DISTRO_DET" ] && [ -d /opt/ros ]; then
  ROS_DISTRO_DET="$(ls /opt/ros 2>/dev/null | head -1)"
fi
RMW="${RMW_IMPLEMENTATION:-por defecto}"
DOMAIN="${ROS_DOMAIN_ID:-0 (valor por defecto)}"

ROS_PKG_VER=""
if [ -n "$ROS_DISTRO_DET" ]; then
  ROS_PKG_VER="$(dpkg-query -W -f='${Version}' "ros-${ROS_DISTRO_DET}-ros-core" 2>/dev/null)"
fi

# ---------------------------------------------------------------------------
# 5. Gazebo
# ---------------------------------------------------------------------------
GZ_VER=""
if command -v gazebo >/dev/null 2>&1; then
  GZ_VER="$(gazebo --version 2>/dev/null | sed -n 's/.*version[[:space:]]*//p' | head -1)"
  GZ_NOMBRE="Gazebo Classic"
elif command -v gz >/dev/null 2>&1; then
  GZ_VER="$(gz --version 2>/dev/null | head -1)"
  GZ_NOMBRE="Gazebo (gz)"
else
  GZ_NOMBRE="Gazebo"
fi
# Respaldo por paquete instalado
if [ -z "$GZ_VER" ]; then
  GZ_VER="$(dpkg-query -W -f='${Version}' gazebo11 2>/dev/null)"
fi
if [ -z "$GZ_VER" ]; then
  GZ_VER="$(dpkg -l 2>/dev/null | awk '/^ii/ && $2 ~ /^(gazebo|libgazebo)/ {print $2" "$3}' | head -3 | tr '\n' ' ')"
fi

# ---------------------------------------------------------------------------
# 6. Paquetes clave de navegacion
# ---------------------------------------------------------------------------
pkgver() {
  local p="$1"
  local v
  v="$(dpkg-query -W -f='${Version}' "$p" 2>/dev/null)"
  od "$v"
}

if [ -n "$ROS_DISTRO_DET" ]; then
  V_SLAM="$(pkgver "ros-${ROS_DISTRO_DET}-slam-toolbox")"
  V_NAV2="$(pkgver "ros-${ROS_DISTRO_DET}-nav2-bringup")"
  V_CTRL="$(pkgver "ros-${ROS_DISTRO_DET}-ros2-control")"
  V_GZROS="$(pkgver "ros-${ROS_DISTRO_DET}-gazebo-ros-pkgs")"
else
  V_SLAM="no detectado"; V_NAV2="no detectado"
  V_CTRL="no detectado"; V_GZROS="no detectado"
fi

# ---------------------------------------------------------------------------
# Informe legible
# ---------------------------------------------------------------------------
informe() {
linea
echo "  DATOS DE LA ESTACION DE TRABAJO"
echo "  Generado el $(date '+%d-%m-%Y %H:%M')"
linea
dato "Sistema operativo:"   "$(od "$SO")"
dato "Kernel:"              "$KERNEL ($ARQ)"
dato "Procesador:"          "$(od "$CPU_MODELO")"
dato "Nucleos fisicos:"     "$(od "$CPU_FISICOS")"
dato "Hilos logicos:"       "$(od "$CPU_HILOS")"
dato "Frecuencia maxima:"   "$( [ -n "$CPU_GHZ" ] && echo "${CPU_GHZ} GHz" || echo 'no detectada' )"
dato "Memoria RAM real:"    "$( [ -n "$RAM_GIB" ] && echo "${RAM_GIB} GiB" || echo 'no detectada' )"
dato "Memoria RAM nominal:" "$( [ -n "$RAM_NOMINAL" ] && echo "${RAM_NOMINAL} GB" || echo 'no detectada' )"
linea
dato "Distribucion ROS 2:"  "$(od "$ROS_DISTRO_DET")"
dato "Paquete ros-core:"    "$(od "$ROS_PKG_VER")"
dato "RMW en uso:"          "$RMW"
dato "ROS_DOMAIN_ID:"       "$DOMAIN"
dato "$GZ_NOMBRE:"          "$(od "$GZ_VER")"
linea
dato "slam_toolbox:"        "$V_SLAM"
dato "nav2_bringup:"        "$V_NAV2"
dato "ros2_control:"        "$V_CTRL"
dato "gazebo_ros_pkgs:"     "$V_GZROS"
linea

# ---------------------------------------------------------------------------
# Bloque listo para pegar en la tesis
# ---------------------------------------------------------------------------
echo
echo "TEXTO LISTO PARA PEGAR EN EL CAPITULO DE RESULTADOS"
linea
cat <<TEXTO
La estacion de trabajo utiliza $(od "$SO"), con procesador $(od "$CPU_MODELO")
de ${CPU_FISICOS:-N} nucleos fisicos y ${RAM_NOMINAL:-N} GB de memoria RAM.
La simulacion se ejecuto en $GZ_NOMBRE $(od "$GZ_VER") sobre ROS 2 $(od "$ROS_DISTRO_DET").
TEXTO
linea
echo
echo "Si algun campo dice 'no detectado', ejecutar el comando manualmente:"
echo "  gazebo --version        (version de Gazebo)"
echo "  lscpu | head -20        (procesador)"
echo "  free -h                 (memoria RAM)"
echo "  lsb_release -a          (sistema operativo)"
}

# ---------------------------------------------------------------------------
# Salida: por pantalla y a un archivo .txt de resguardo
#   Ruta por defecto: datos_estacion_AAAAMMDD_HHMM.txt en el directorio actual
#   Ruta alternativa: bash datos_estacion.sh /ruta/mi_archivo.txt
# ---------------------------------------------------------------------------
SALIDA="${1:-datos_estacion_$(date '+%Y%m%d_%H%M').txt}"

informe | tee "$SALIDA"

echo
if [ -s "$SALIDA" ]; then
  echo "Resguardo guardado en: $(readlink -f "$SALIDA")"
else
  echo "AVISO: no se pudo escribir el archivo de resguardo en $SALIDA."
  echo "Revisar permisos de escritura del directorio o indicar otra ruta:"
  echo "  bash datos_estacion.sh \$HOME/datos_estacion.txt"
fi
