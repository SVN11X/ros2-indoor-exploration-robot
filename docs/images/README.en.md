# images

Spanish version: [README.md](README.md)

Photos and screenshots of the project, sorted by topic. Result plots are not here: the scripts generate them, and they stay next to their experiment in `experiments/` and in `firmware/pid_config/`.

## What goes here

- `robot/`: photos of the prototype.
- `field-tests/`: photos of the experiments on the real robot.
- `simulation/`: Gazebo and RViz with the digital twin.
- `real-robot/`: RViz during mapping and navigation on the real robot.

Screenshots of the installation guides stay next to their guide, in `docs/robot-setup/`.

## Naming

kebab-case in English, describing what the image shows. When there are several of the same kind, they end in the date `YYYY-MM-DD` or a number.

## Robot

| | |
| --- | --- |
| <img src="robot/robot-front.jpg" width="200" alt="Front view of the robot"> | <img src="robot/robot-front-left.jpg" width="200" alt="Diagonal view of the robot"> |
| Front view, with the camera in the middle and the LIDAR on top. | Diagonal view. |
| <img src="robot/robot-side.jpg" width="200" alt="Side view of the robot"> | <img src="robot/robot-top.jpg" width="200" alt="Top view of the robot"> |
| Side view. | Top view, with the LIDAR and the voltage, current and power meter. |

## Field tests

Odometry tests on the real robot, on carpet, with tape as reference (March 25, 2026). The results are in `experiments/linea_recta/` and `experiments/prueba_giro/`.

| | |
| --- | --- |
| <img src="field-tests/odometry-test-robot-on-marks-1.jpg" width="200" alt="Robot next to the test marks"> | <img src="field-tests/odometry-test-robot-on-marks-2.jpg" width="200" alt="Robot next to the marks, another view"> |
| Robot next to the test marks. | The same position, seen from the other side. |
| <img src="field-tests/odometry-test-marks.jpg" width="200" alt="Numbered marks on the floor"> | <img src="field-tests/odometry-test-reference-line.jpg" width="200" alt="Reference tape line"> |
| Numbered marks of each repetition. | Tape line used as reference. |

## Simulation

| | |
| --- | --- |
| <img src="simulation/gazebo-obstacles-world.jpg" width="360" alt="Test world in Gazebo"> | <img src="simulation/obstacles-world-layout.png" width="300" alt="Layout of the test world"> |
| Test world with obstacles in Gazebo Classic. | World layout: 6 m by 8 m, boxes B1 to B8 and cylinders C1 to C6. |
| <img src="simulation/rviz-robot-model.png" width="360" alt="Robot model in RViz"> | <img src="simulation/rviz-simulated-lidar-scan.png" width="360" alt="Simulated LIDAR scan"> |
| URDF robot model in RViz. | Points of the simulated LIDAR. |
| <img src="simulation/mapping-rviz-and-gazebo.png" width="360" alt="Mapping in RViz and Gazebo"> | <img src="simulation/mapping-start.png" width="360" alt="Start of mapping"> |
| Mapping in simulation: RViz on the left and Gazebo on the right. | Start of mapping with the first scans. |
| <img src="simulation/mapping-costmap-progress.png" width="360" alt="Costmap during mapping"> | <img src="simulation/nav2-goal-pose.png" width="360" alt="Navigation goal"> |
| Costmap during mapping. | Navigation goal set with 2D Goal Pose. |
| <img src="simulation/straight-path-in-rviz.png" width="360" alt="Straight path in RViz"> | <img src="simulation/robot-footprint-on-costmap.png" width="360" alt="Robot footprint on the costmap"> |
| Straight path recorded in RViz. | Robot footprint on the costmap. |
| <img src="simulation/exploration-early-scan.png" width="360" alt="Start of exploration"> | <img src="simulation/exploration-inflated-obstacles.png" width="360" alt="Inflated obstacles"> |
| Start of frontier exploration. | Safety zone around the cylinders. |
| <img src="simulation/exploration-costmap.png" width="360" alt="Costmap during exploration"> | <img src="simulation/exploration-map-overview.png" width="360" alt="Overview of the explored map"> |
| Costmap during exploration. | Overview of the explored map. |

## Real robot

| | |
| --- | --- |
| <img src="real-robot/mapping-apartment-2026-01-01.png" width="360" alt="Map of a room"> | <img src="real-robot/navigation-planned-path-2026-01-16.png" width="360" alt="Path planned by Nav2"> |
| Map of a room with its costmap (January 1, 2026). | Path planned by Nav2 with the LIDAR scans (January 16). |
| <img src="real-robot/mapping-corridor-2026-01-17-1.png" width="360" alt="Corridor mapping, 1"> | <img src="real-robot/mapping-corridor-2026-01-17-2.png" width="360" alt="Corridor mapping, 2"> |
| Mapping a corridor, capture 1 (January 17). | Capture 2, same day. |
| <img src="real-robot/mapping-corridor-2026-01-17-3.png" width="360" alt="Corridor mapping, 3"> | <img src="real-robot/mapping-corridor-2026-01-17-4.png" width="360" alt="Corridor mapping, 4"> |
| Capture 3. | Capture 4. |
| <img src="real-robot/mapping-room-annotated-2026-01-24.png" width="360" alt="Map of a room with marked areas"> | <img src="real-robot/navigation-room-path-2026-01-24.png" width="360" alt="Navigation path in the room"> |
| Map of a room with two areas marked by hand (January 24). | Navigation path in the same room. |
| <img src="real-robot/odom-topic-rate-30hz.png" width="200" alt="Rate of the odom topic"> | |
| `ros2 topic hz /odom`: odometry is published at about 30 Hz. | |

The videos of the experiments are in [docs/videos/](../videos/README.en.md).
