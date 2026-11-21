# How it works

<!-- An AI tool may draft this file from the real code, never from a guess. It stays a draft until the owner confirms it. Update it in the same change that alters the main flow. Paths in backticks must exist: the check reads them. -->

Status: draft. Written from the launch scripts and the thesis, waiting for the owner's confirmation.

The repository root is a ROS 2 Foxy colcon workspace. The PC clones it as `~/tesis_black_robot` and the Raspberry Pi keeps it as `~/robot_ws`.

## From start to finish

A mapping session with autonomous exploration on the real robot:

1. On the Raspberry Pi, `scripts/launch/launch_robot_all.sh` starts `src/articubot_one/launch/launch_robot.launch.py`. It publishes the robot model and starts ros2_control with the DiffDriveArduino hardware interface (plugin diffdrive_arduino/DiffDriveArduino), which talks to the Arduino over `/dev/motor_controller` at 57600 baud.
2. The Arduino runs `firmware/ROSArduinoBridge/ROSArduinoBridge.ino`. It reads the encoders, runs the wheel speed controller and drives the L298N.
3. The same script spawns the `diff_cont` controller, which publishes odometry, and starts the LIDAR with `src/articubot_one/launch/rplidar.launch.py`, which publishes `/scan`.
4. On the PC, `scripts/launch/launch_mapeo_all.sh` starts teleoperation with twist_mux, RViz, SLAM Toolbox with `src/articubot_one/config/mapper_params_online_async.yaml` and Nav2 with `src/articubot_one/config/nav2_params.yaml`.
5. For each iteration it calls `experiments/exploracion/run_explore.sh`, which runs the frontier explorer with `src/articubot_one/config/explore.yaml`, saves the map and the logs, and stops when no frontiers are left.
6. The results land in `experiments/sesiones_mapeo/` and the analysis scripts in `experiments/slam/` and `experiments/mapas_vs_plano/` compute the metrics the thesis reports.

The simulation follows the same steps with `scripts/launch/launch_sim_all.sh`, which starts Gazebo Classic through `src/articubot_one/launch/launch_sim.launch.py` and uses the GazeboSystem plugin of gazebo_ros2_control instead of the Arduino.

## Parts

- `src/articubot_one/`: the robot package. URDF and xacro model, launch files, and the SLAM, Nav2, controller and exploration parameters.
- `src/serial_motor_demo/`: a serial motor test package with its message definitions.
- `src/third_party/`: packages that come from other projects. `diffdrive_arduino` (hardware interface), `gazebo_ros2_control` (simulation backend), `m-explore-ros2` (frontier explorer), `serial` (serial port library) and `joy_tester`. The thesis adapted `diffdrive_arduino` and `m-explore-ros2` for this robot. Origins and licenses are in `docs/credits.md`.
- `firmware/ROSArduinoBridge/`: the Arduino Nano firmware.
- `firmware/pid_config/`: PID identification and tuning with PSO and Lambda, and the stability analysis.
- `mechanical/`: 3D models of the built robot, its first chassis design and its parts.
- `scripts/launch/`: full start of the robot, the simulation and the mapping sessions.
- `scripts/robot-setup/`: Raspberry Pi diagnostics and tuning.
- `experiments/`: thesis experiments, their scripts and recorded results.
- `docs/robot-setup/`: installation guides for Ubuntu, ROS 2, networking and exploration.

## Where to start reading

`scripts/launch/launch_robot_all.sh` and `scripts/launch/launch_mapeo_all.sh`. They show the order in which every node starts and which configuration file each one reads.

## Run it and check it

Build from the workspace root:

```bash
colcon build --symlink-install
source install/setup.bash
```

Simulation on the PC:

```bash
bash scripts/launch/launch_sim_all.sh
```

Real robot: `bash ~/robot_ws/scripts/launch/launch_robot_all.sh` on the Raspberry Pi, then `bash scripts/launch/launch_mapeo_all.sh` on the PC. The launch scripts wait for the `odom` to `base_link` and `base_link` to `laser_frame` transforms before they continue, which is the first proof that the robot works.

`docs/images/diagrams/ros-graph.png` shows the nodes and topics of a running system, and `docs/images/diagrams/tf-tree-simulation.pdf` and `docs/images/diagrams/tf-tree-real-robot.pdf` show the transform tree to expect in each case.

## Not covered

- Navigation to fixed goals set by an operator. `experiments/navegacion/run_prueba_nav.sh` is prepared but was not run (thesis annex 8).
- Localization on a stored map with AMCL.
- Automated tests. Every experiment needs the robot or Gazebo.
