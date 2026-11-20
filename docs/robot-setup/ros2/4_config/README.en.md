# Setup Guide: URDF and Real Hardware

Spanish version: [README.md](README.md)

Guide to build, launch the simulation, and set up the camera and joystick on the Raspberry Pi and the PC.

> **Requirement:** ROS 2 Foxy and `colcon` installed.

## 1. Prepare the Workspace

Go to the root folder of this repository:

```bash
cd ~/tesis_black_robot
```

## 2. Install General Dependencies

Run this block to install the basic dependencies of the robot and the simulation.

```bash
# 1. Actualizar dependencias del sistema y rosdep
sudo rosdep init
rosdep update
rosdep install --from-paths src --ignore-src -r -y

# 2. Instalar paquetes críticos de ROS (Control, Xacro y GUI)
# Nota: La barra invertida (\) permite dividir el comando en varias líneas.
sudo apt install ros-foxy-xacro \
                 ros-foxy-joint-state-publisher-gui \
                 ros-foxy-ros2-control \
                 ros-foxy-ros2-controllers \
                 ros-foxy-controller-manager \
                 ros-foxy-async-web-server-cpp \
                 ros-foxy-slam-toolbox

# 3. Instalar navegación y utilidades
sudo apt install ros-foxy-navigation2 ros-foxy-nav2-bringup                 
sudo apt install ros-foxy-twist-mux
```

## 3. Build

Use the `--symlink-install` option to ease development (changes to Python and XML files apply without rebuilding).

```bash
colcon build --symlink-install
```

## 4. Run (Launch)

Once built, load the environment and launch the robot:

```bash
source install/setup.bash
ros2 launch articubot_one rsp.launch.py
```

## 5. Visualization (RViz)

To see the model and its joints:

1.  Open a **new terminal**.
2.  Load the environment and open RViz:
    ```bash
    cd ~/tesis_black_robot
    source install/setup.bash
    ros2 run rviz2 rviz2 -d /home/$USER/tesis_black_robot/src/articubot_one/config/view_bot.rviz
    ```
3.  To move the wheels by hand, open **another terminal** and run:
    ```bash
    ros2 run joint_state_publisher_gui joint_state_publisher_gui
    ```

---

## 6. Real Hardware Setup (Raspberry Pi Camera)

### 6.1. On the Raspberry Pi (Robot)
Install the drivers to capture video and the plugins to compress the stream (avoids lag over Wi-Fi). 
*Note: `libraspberrypi-bin` was removed for compatibility with standard Ubuntu.*

```bash
# Drivers de video y nodo de cámara ROS
sudo apt install v4l-utils ros-foxy-v4l2-camera

# Plugins de transporte (necesario para enviar imagen comprimida)
sudo apt install ros-foxy-image-transport-plugins
```

### 6.2. On the PC (Control Station)
Install the tools to decompress and view the video stream.

```bash
# Plugins de transporte (necesario para descomprimir la imagen recibida)
sudo apt install ros-foxy-image-transport-plugins

# Herramienta visual (GUI)
sudo apt install ros-foxy-rqt-image-view
```

---

## 7. Joystick Setup (Teleoperation)

> **Note:** These steps usually run on the **PC (Control Station)**, where the USB or Bluetooth controller is connected.

### 7.1. Linux Tools and Drivers
First, install the system utilities to check that Linux recognizes the hardware (gamepad or controller).

```bash
sudo apt install joystick jstest-gtk evtest
```

### 7.2. ROS 2 Joystick Package
Install the joystick driver node for ROS 2:

```bash
sudo apt install ros-foxy-joy-linux
```
