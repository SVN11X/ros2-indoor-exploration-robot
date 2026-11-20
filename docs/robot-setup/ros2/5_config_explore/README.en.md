# Exploration Setup (m-explore-ros2)

Spanish version: [README.md](README.md)

The package is already included in `src/third_party/m-explore-ros2/`. These steps are only needed to reproduce it from scratch: clone the package, install its dependencies, and replace the `.hpp` includes with the `.h` headers that ROS 2 Foxy ships.

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
