# Base Environment Setup: ROS 2 Foxy and Gazebo

Spanish version: [README.md](README.md)

This guide prepares a clean **Ubuntu 20.04** system with the tools needed for robot development.

## 1. Install ROS 2 Foxy

ROS 2 Foxy Fitzroy is the version this project requires. Since it no longer has official support, the repositories must be set up by hand.

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

## 2. Development Tools

Install the build system (`colcon`) and the dependency manager (`rosdep`).

```bash
sudo apt install python3-colcon-common-extensions python3-rosdep
```

## 3. Install Gazebo

The physics simulation uses Gazebo Classic with the ROS 2 bridge packages.

```bash
sudo apt install ros-foxy-gazebo-ros-pkgs
```

## 4. Automatic Environment Setup

To avoid setting the variables by hand in every terminal, add them to the `.bashrc` file. It includes the `LC_NUMERIC` fix to avoid graphics errors in RViz caused by the system language.

```bash
# Agregar el entorno de ROS 2
echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc

# Agregar corrección de formato numérico para RViz (Evita error GLSL)
echo 'export LC_NUMERIC="en_US.UTF-8"' >> ~/.bashrc

# Recargar la configuración
source ~/.bashrc
```

## 5. Verification

To confirm everything installed correctly, open a terminal and run the example node:

```bash
ros2 run demo_nodes_cpp talker
```
*(You should see "Publishing: Hello World" messages on screen).*
