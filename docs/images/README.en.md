# images

Spanish version: [README.md](README.md)

Photos and screenshots of the project, sorted by topic. Result plots are not here: the scripts generate them, and they stay next to their experiment in `experiments/` and in `firmware/pid_config/`.

## What goes here

- `robot/`: photos of the prototype.
- `field-tests/`: photos of the experiments on the real robot.
- `simulation/`: Gazebo and RViz with the digital twin.
- `real-robot/`: RViz during mapping and navigation on the real robot.
- `mechanical/`: images of the 3D models in `mechanical/`, made from their STEP files, and Fusion 360 renders.
- `diagrams/`: thesis diagrams with their source PowerPoint, and the TF trees in PDF.
- `components/`: photos of the parts, from stores or manufacturers.

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
| <img src="robot/robot-front-close.jpg" width="200" alt="Front view of the robot, closer"> | <img src="robot/robot-right-side-close.jpg" width="200" alt="Right side view of the robot"> |
| Front view, closer. | Right side view, closer. |
| <img src="robot/robot-front-right-close.png" width="200" alt="Front and right side view of the robot"> |  |
| Front and right side view, closer. |  |

## 3D models

The models are in [mechanical/](../../mechanical/README.en.md). The images with parts use the same numbers.

| | |
| --- | --- |
| <img src="mechanical/robot-v2.png" width="200" alt="3D model of the built robot"> | <img src="mechanical/robot-v2-inside.png" width="200" alt="Inside of the 3D model with the parts numbered"> |
| The built robot (v2). | The inside of v2 with the parts numbered. |
| <img src="mechanical/robot-v1.png" width="200" alt="First chassis design"> | <img src="mechanical/motor-control-stack.png" width="200" alt="Arduino Nano, terminal adapter and L298N driver"> |
| First chassis design (v1). | The Arduino Nano, its terminal adapter and the L298N driver. |
| <img src="mechanical/components.png" width="200" alt="The 11 part models"> | |
| The 11 part models, with their file names. | |
| <img src="mechanical/robot-v2-render-top-left-front.png" width="200" alt="Fusion 360 render of v2, top left view, front"> | <img src="mechanical/robot-v2-render-top-left-back.png" width="200" alt="Fusion 360 render of v2, top left view, back"> |
| Fusion 360 render of v2. Top left view, front. | Fusion 360 render of v2. Top left view, back. |
| <img src="mechanical/robot-v2-render-top-right.png" width="200" alt="Fusion 360 render of v2, top right view"> | <img src="mechanical/robot-v2-render-bottom-right.png" width="200" alt="Fusion 360 render of v2, bottom right view"> |
| Fusion 360 render of v2. Top right view. | Fusion 360 render of v2. Bottom right view. |

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
| <img src="simulation/gazebo-scenario-overview.jpg" width="360" alt="Visual Gazebo scenario with people, posts and a numbered block"> | <img src="simulation/gazebo-scenario-close.jpg" width="360" alt="The same scenario, closer to the robot"> |
| Visual Gazebo scenario with people, posts and a numbered block. | The same scenario, closer to the robot. |
| <img src="simulation/gazebo-camera-view.jpg" width="360" alt="Field of view of the simulated camera"> | <img src="simulation/rviz-lidar-scan-obstacles.png" width="360" alt="Simulated LIDAR scan over the obstacles, in RViz"> |
| Field of view of the simulated camera. | Simulated LIDAR scan over the obstacles, in RViz. |
| <img src="simulation/rviz-costmap-scan.png" width="360" alt="Costmap and LIDAR scan in RViz"> | <img src="simulation/rviz-tf-frames.png" width="360" alt="Axes of the robot TF frames in RViz"> |
| Costmap and LIDAR scan in RViz. | Axes of the robot TF frames in RViz. |
| <img src="simulation/navigation-sample-1.png" width="360" alt="Navigation in simulation, Gazebo on the left and RViz on the right, moment 1"> | <img src="simulation/navigation-sample-2.png" width="360" alt="Moment 2"> |
| Navigation in simulation, Gazebo on the left and RViz on the right, moment 1. | Moment 2. |
| <img src="simulation/navigation-sample-3.png" width="360" alt="Moment 3"> |  |
| Moment 3. |  |

The odometry tests in Gazebo are in [experiments/](../../experiments/README.en.md#odometry).

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

## Diagrams

Thesis figures. Each PNG has its source PowerPoint next to it, with the same name and the `.pptx` extension. The README of each folder shows them where they explain something.

- General: [digital twin](diagrams/digital-twin-sync.png), [repository on the PC and on the robot](diagrams/workspace-folders.png), [wiring](diagrams/wiring-diagram.png) and [power use](diagrams/power-budget.png).
- Firmware: [files](diagrams/firmware-file-tree.png), [architecture](diagrams/firmware-architecture.png), [startup](diagrams/firmware-startup-sequence.png), [control cycle](diagrams/firmware-control-sequence.png), [unit conversion](diagrams/ros2-control-unit-conversion.png) and [encoder states](diagrams/encoder-quadrature-states.jpg).
- ROS 2: [xacro files](diagrams/xacro-file-structure.png), [choice between the real robot and simulation](diagrams/xacro-decision-tree.png), [from xacro to /tf](diagrams/urdf-to-tf-flow.png), [startup order](diagrams/launch-startup-sequence.png), [differential control](diagrams/differential-control-flow.png), [Gazebo differential drive plugin](diagrams/gazebo-diff-drive-plugin.png), [Nav2 behavior tree](diagrams/nav2-behavior-tree.png) and [running nodes and topics](diagrams/ros-graph.png).
- Validation: [digital twin validation](diagrams/validation-flowchart.png), and the TF trees of the [simulation](diagrams/tf-tree-simulation.pdf) and of the [real robot](diagrams/tf-tree-real-robot.pdf).

Most have a transparent background and dark text, so they read best with the GitHub light theme.

## Parts

Photos from stores or manufacturers. Their source is not recorded, as `docs/credits.md` says.

|  |  |  |
| --- | --- | --- |
| <img src="components/rplidar-a1m8.jpg" width="140" alt="RPLidar A1M8"> | <img src="components/arduino-nano.jpg" width="140" alt="Arduino Nano"> | <img src="components/l298n-driver.png" width="140" alt="L298N driver"> |
| RPLidar A1M8 | Arduino Nano | L298N driver |
| <img src="components/jga25-370-motor.jpg" width="140" alt="JGA25-370 gear motor"> | <img src="components/motor-encoder-pinout.jpg" width="140" alt="Wires of the motor with encoder"> | <img src="components/wheels.png" width="140" alt="Wheels"> |
| JGA25-370 gear motor | Wires of the motor with encoder | Wheels |
| <img src="components/ball-caster.png" width="140" alt="Caster wheel"> | <img src="components/battery.png" width="140" alt="12 V battery"> | <img src="components/dc-dc-power-module.jpg" width="140" alt="DFRobot DFR0205 DC-DC buck module"> |
| Caster wheel | 12 V battery | DFRobot DFR0205 DC-DC buck module |
| <img src="components/raspberry-pi-camera.jpg" width="140" alt="Raspberry Pi camera"> | <img src="components/power-switch.jpg" width="140" alt="Power switch"> | <img src="components/blade-fuse.jpg" width="140" alt="Blade fuse"> |
| Raspberry Pi camera | Power switch | Blade fuse |
| <img src="components/travel-router.png" width="140" alt="GL.iNet GL-MT300N-V2 travel router"> | <img src="components/pla-plus-filament.png" width="140" alt="PLA+ filament"> | <img src="components/ender-3-printer.jpg" width="140" alt="Ender 3 3D printer"> |
| GL.iNet GL-MT300N-V2 travel router | PLA+ filament | Ender 3 3D printer |
