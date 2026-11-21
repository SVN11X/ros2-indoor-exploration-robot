# Credits

Code in this repository that comes from other projects. Origins follow table A3.1 and the bibliography of the thesis. Licenses come from each package's LICENSE file or package.xml. The MIT license in `LICENSE` covers only the author's own code, not these packages. The upstream repositories of articubot_one, serial_motor_demo and ros_arduino_bridge declare no license on GitHub (checked 2026-11-20).

| Path | Origin | License | Changes for this robot |
| --- | --- | --- | --- |
| `src/articubot_one/` | [joshnewans/articubot_one](https://github.com/joshnewans/articubot_one) (Newans, 2023) | Not declared in package.xml | Model, control, SLAM, navigation, exploration and simulation configuration |
| `src/third_party/diffdrive_arduino/` | [joshnewans/diffdrive_arduino](https://github.com/joshnewans/diffdrive_arduino) (Newans, 2022a) | BSD (package.xml) | Adapted, per thesis table A3.1 |
| `src/third_party/m-explore-ros2/` | [robo-friends/m-explore-ros2](https://github.com/robo-friends/m-explore-ros2) (Alvarez, 2021), ROS 2 port of [hrnr/m-explore](https://github.com/hrnr/m-explore) | BSD (LICENSE) | Adapted, per thesis table A3.1 |
| `src/third_party/gazebo_ros2_control/` | [ros-controls/gazebo_ros2_control](https://github.com/ros-controls/gazebo_ros2_control) | Apache 2.0 (LICENSE) | None recorded |
| `src/third_party/serial/` | [wjwwood/serial](https://github.com/wjwwood/serial) | MIT (package.xml) | None recorded |
| `src/third_party/joy_tester/` | Josh Newans, joy_tester | Apache 2.0 (LICENSE) | None recorded |
| `src/serial_motor_demo/` | [joshnewans/serial_motor_demo](https://github.com/joshnewans/serial_motor_demo) | Not declared in package.xml | None recorded |
| `firmware/ROSArduinoBridge/` | [joshnewans/ros_arduino_bridge](https://github.com/joshnewans/ros_arduino_bridge) (Newans, 2022b), fork of [hbrobotics/ros_arduino_bridge](https://github.com/hbrobotics/ros_arduino_bridge) | BSD (source header) | Gains and physical constants for this robot, per thesis section 4.4 |

## 3D models

The MIT license in `LICENSE` does not cover the third-party models below. The owner did not record where the part models were downloaded.

| Path | Origin | License |
| --- | --- | --- |
| `mechanical/robot/` | The author's design. The chassis takes as reference the [Vacuum Robot](https://www.thingiverse.com/thing:4459513) by marcuslanzoni (2020) on Thingiverse, per thesis section 4.1.1. The v2 model includes five of the part models below. | Vacuum Robot: not recorded. Thingiverse refused an automated check on 2026-11-21 |
| `mechanical/components/` | 11 third-party part models. Source not recorded | Not recorded |
