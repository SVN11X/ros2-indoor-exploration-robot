# src

Spanish version: [README.md](README.md)

ROS 2 packages of the workspace. colcon finds them at any depth inside this folder.

## What goes here

- `articubot_one/`: URDF and xacro robot model, launch files, and the control, SLAM, Nav2, exploration and simulation parameters.
- `serial_motor_demo/`: serial motor test package and its messages.
- `third_party/`: packages that come from other projects. Their origin and license are in `docs/credits.md`.

## What does not go here

- Arduino firmware (it goes in `firmware/`).
- Launch scripts (they go in `scripts/launch/`).
- Thesis experiments and their results (they go in `experiments/`).
- colcon output (`build/`, `install/` and `log/` stay at the root and are ignored).

## Naming

Each package uses the name its `package.xml` declares, in snake_case.
