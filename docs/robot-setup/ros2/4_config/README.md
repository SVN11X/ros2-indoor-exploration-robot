# Guía de Configuración: URDF y Hardware Real

Versión en inglés: [README.en.md](README.en.md)

Guía para compilar, lanzar la simulación y configurar la cámara y joystick en la Raspberry Pi/PC.

> **Requisito:** Tener instalado ROS 2 Foxy y `colcon`.

## 1. Preparación del Workspace

Accede a la carpeta raíz de este repositorio:

```bash
cd ~/tesis_black_robot
```

## 2. Instalación de Dependencias Generales

Ejecuta este bloque para instalar las dependencias básicas del robot y la simulación.

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

## 3. Compilación

Utiliza la opción `--symlink-install` para facilitar el desarrollo (los cambios en Python/XML se reflejan sin recompilar).

```bash
colcon build --symlink-install
```

## 4. Ejecución (Launch)

Una vez compilado, carga el entorno y lanza el robot:

```bash
source install/setup.bash
ros2 launch articubot_one rsp.launch.py
```

## 5. Visualización (RViz)

Para ver el modelo y las articulaciones:

1.  Abre una **nueva terminal**.
2.  Carga el entorno y abre RViz:
    ```bash
    cd ~/tesis_black_robot
    source install/setup.bash
    ros2 run rviz2 rviz2 -d /home/$USER/tesis_black_robot/src/articubot_one/config/view_bot.rviz
    ```
3.  Para mover las ruedas manualmente, abre **otra terminal** y ejecuta:
    ```bash
    ros2 run joint_state_publisher_gui joint_state_publisher_gui
    ```

---

## 6. Configuración de Hardware Real (Raspberry Pi Camera)

### 6.1. En la Raspberry Pi (Robot)
Instalación de drivers para capturar video y plugins para comprimir la transmisión (evita lag en WiFi). 
*Nota: Se eliminó `libraspberrypi-bin` para compatibilidad con Ubuntu estándar.*

```bash
# Drivers de video y nodo de cámara ROS
sudo apt install v4l-utils ros-foxy-v4l2-camera

# Plugins de transporte (necesario para enviar imagen comprimida)
sudo apt install ros-foxy-image-transport-plugins
```

### 6.2. En el PC (Control Station)
Instalación de herramientas para descomprimir la señal de video y visualizarla.

```bash
# Plugins de transporte (necesario para descomprimir la imagen recibida)
sudo apt install ros-foxy-image-transport-plugins

# Herramienta visual (GUI)
sudo apt install ros-foxy-rqt-image-view
```

---

## 7. Configuración de Joystick (Teleoperación)

> **Nota:** Estos pasos se suelen realizar en el **PC (Control Station)** donde está conectado el mando USB/Bluetooth.

### 7.1. Instalación de Herramientas y Drivers en Linux
Primero, es necesario instalar las utilidades del sistema para verificar que Linux reconoce el hardware (gamepad/control).

```bash
sudo apt install joystick jstest-gtk evtest
```

### 7.2. Paquete ROS 2 para Joystick
Instala el nodo driver de joystick para ROS 2:

```bash
sudo apt install ros-foxy-joy-linux
```