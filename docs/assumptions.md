# Assumptions

Things taken as true without confirmation. Review the open ones in every pull request. Status is open, confirmed or discarded.

| Date | Assumption | Made by | Task | Status |
|------|------------|---------|------|--------|
| 2026-11-20 | The Raspberry Pi gets the new layout by pulling the repository into `~/robot_ws`. | Claude Code | Order folders (PR #1) | confirmed: the owner said `~/robot_ws` is a clone of this repository under another name |
| 2026-11-20 | `~/robot_ws/test/recursos/` and `~/tesis_black_robot/test/recursos/`, used by `launch_mapeo_all.sh`, `monitor_pi.sh` and `monitor_sim.sh`, are folders outside the repository, so they stay unchanged. | Claude Code | Order folders (PR #1) | partly discarded: `launch_mapeo_all.sh` now runs `monitor_pi.sh` from `~/robot_ws/experiments/recursos/`, where the clone keeps it. Result folders stay unchanged |
| 2026-11-20 | `src/serial_motor_demo/` comes from joshnewans/serial_motor_demo, as its README and the firmware README suggest. | Claude Code | Order folders (PR #1) | open |
| 2026-11-21 | `mechanical/robot/robot-v1` (formerly `Tesis.stp`) is a first chassis design that came before the built robot, because `robot-v2` matches the photos of the robot. | Claude Code | 3D models | open |
| 2026-11-21 | `mechanical/components/rplidar-a1-mount.step` (formerly `RPLIDAR+A1M8.stp`) is a mount for the LIDAR, judging by its shape. | Claude Code | 3D models | open |
| 2026-11-21 | `mechanical/components/dfrobot-power-module.step` is the 25 W DC-DC buck module of thesis table A1.1. The README only states the two facts side by side. | Claude Code | 3D models | open |
