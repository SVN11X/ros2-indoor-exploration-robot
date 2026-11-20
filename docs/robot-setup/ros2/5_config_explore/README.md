# Configuración de la exploración (m-explore-ros2)

Versión en inglés: [README.en.md](README.en.md)

El paquete ya está incluido en `src/third_party/m-explore-ros2/`. Estos pasos solo hacen falta para reproducirlo desde cero: clonar el paquete, instalar sus dependencias y cambiar los includes `.hpp` por los `.h` que trae ROS 2 Foxy.

```bash
cd ~/tesis_black_robot/src/third_party
git clone https://github.com/robo-friends/m-explore-ros2.git

cd ~/tesis_black_robot
rosdep update
rosdep install --from-paths src --ignore-src -r -y

cd ~/tesis_black_robot
grep -rl "tf2_ros/buffer.hpp" src/third_party/m-explore-ros2 | xargs sed -i 's|tf2_ros/buffer.hpp|tf2_ros/buffer.h|g'
grep -rl "tf2_ros/.*\.hpp" src/third_party/m-explore-ros2 | xargs sed -i 's|tf2_ros/\(.*\)\.hpp|tf2_ros/\1.h|g'
grep -rl "tf2_geometry_msgs/.*\.hpp" src/third_party/m-explore-ros2 | xargs sed -i 's|tf2_geometry_msgs/\(.*\)\.hpp|tf2_geometry_msgs/\1.h|g'
grep -rl "tf2/.*\.hpp" src/third_party/m-explore-ros2 | xargs sed -i 's|tf2/\(.*\)\.hpp|tf2/\1.h|g'
```
