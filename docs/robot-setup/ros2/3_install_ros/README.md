# Configuración del Entorno Base: ROS 2 Foxy y Gazebo

Versión en inglés: [README.en.md](README.en.md)

Esta guía detalla los pasos para preparar un sistema **Ubuntu 20.04** limpio con las herramientas necesarias para el desarrollo robótico.

## 1. Instalación de ROS 2 Foxy

ROS 2 Foxy Fitzroy es la versión requerida para este proyecto. Como ya no tiene soporte oficial, es necesario configurar los repositorios manualmente.

```bash
# 1. Habilitar herramientas del sistema y repositorio Universe
sudo apt update && sudo apt install curl gnupg2 lsb-release
sudo apt install software-properties-common
sudo add-apt-repository universe

# 2. Autorizar llave GPG de ROS
sudo curl -sSL [https://raw.githubusercontent.com/ros/rosdistro/master/ros.key](https://raw.githubusercontent.com/ros/rosdistro/master/ros.key) -o /usr/share/keyrings/ros-archive-keyring.gpg

# 3. Agregar repositorio a sources.list
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] [http://packages.ros.org/ros2/ubuntu](http://packages.ros.org/ros2/ubuntu) $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null

# 4. Instalar ROS 2 Foxy Desktop (Base + Herramientas GUI + Demos)
sudo apt update
sudo apt install ros-foxy-desktop
```

## 2. Herramientas de Desarrollo

Instalaremos el sistema de compilación (`colcon`) y el gestor de dependencias (`rosdep`).

```bash
sudo apt install python3-colcon-common-extensions python3-rosdep
```

## 3. Instalación de Gazebo

Para la simulación física se utiliza Gazebo Classic junto con los paquetes puente de ROS 2.

```bash
sudo apt install ros-foxy-gazebo-ros-pkgs
```

## 4. Configuración Automática del Entorno

Para no tener que configurar las variables manualmente en cada terminal, las agregaremos al archivo `.bashrc`. Se incluye la corrección `LC_NUMERIC` para evitar errores gráficos en RViz debido al idioma del sistema.

```bash
# Agregar el entorno de ROS 2
echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc

# Agregar corrección de formato numérico para RViz (Evita error GLSL)
echo 'export LC_NUMERIC="en_US.UTF-8"' >> ~/.bashrc

# Recargar la configuración
source ~/.bashrc
```

## 5. Verificación

Para confirmar que todo se instaló correctamente, abre una terminal y ejecuta el nodo de ejemplo:

```bash
ros2 run demo_nodes_cpp talker
```
*(Deberías ver mensajes "Publishing: Hello World" en pantalla).*