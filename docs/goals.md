# Goals

<!-- Written by the owner. AI tools may format or translate this file, never invent its content. Replace every TODO(owner) line. -->

Transcribed from the owner's final thesis, "Navegación y exploración autónoma de interiores utilizando un robot móvil de tracción diferencial" (UTEM, 2026), sections Objetivo general, Objetivos específicos and Alcances y limitaciones.

## Vision

A low-cost differential drive robot, based on ROS 2, that builds a 2D map of an indoor space with SLAM and navigates on its own toward frontier goals generated automatically.

## Users

Anyone can use this repository (owner, 2026-11-20).

## Objectives

1. Design and build a differential drive robot, validated first with a digital twin in Gazebo Classic.
2. Implement low-level control: differential kinematics, encoder odometry and a closed-loop PID on the wheel speeds.
3. Implement localization, 2D mapping and autonomous navigation with SLAM Toolbox and Nav2.
4. Integrate frontier-based exploration that sends goals toward unmapped areas without continuous manual input.

## Non-goals

- Navigation to fixed goals set by an operator, with success rate and final position error. Left as future work.
- Localization on a stored map with AMCL. The node is present with default parameters but is not tuned or used in any experiment.
- Outdoor use, uneven floors and fast dynamic obstacles.
- IMU, camera or sensor fusion.

## Success criteria

Results reported by the thesis (abstract):

- Odometry mean error of 3.63 % on straight paths on the real robot.
- Wheel speed control at 0.13 m/s with steady-state error close to zero and no visible overshoot.
- Valid maps in 5 of 6 exploration runs, mean free coverage index of 62.2 % and mean mapped free area of 3.50 m².
- Mean distance of 3.4 cm between the maps and a measured floor plan.

## Priorities

From the owner, 2026-11-20:

1. The code works and is final. Keep its behavior.
2. Order folders and files. Code changes are allowed only when a move needs them.

## Constraints

- ROS 2 Foxy on Ubuntu 20.04 LTS, Gazebo Classic 11. Frozen at the start of the project for package compatibility.
- Hardware: Raspberry Pi 4, Arduino Nano, L298N driver, DC motors with quadrature encoders, RPLidar A1.
- The code is final. Changes are limited to file locations, the paths that depend on them, and comments.
