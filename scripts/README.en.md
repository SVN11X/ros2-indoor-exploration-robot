# scripts

Spanish version: [README.md](README.md)

Scripts that launch the system and prepare the Raspberry Pi.

## What goes here

- `launch/`: full start of the real robot (`launch_robot_all.sh`), of the simulation (`launch_sim_all.sh`) and of the mapping sessions with exploration (`launch_mapeo_all.sh`). The `mapeo*.txt` files keep the commands of each mode.
- `robot-setup/`: Raspberry Pi diagnostics and tuning, such as system health (`check_salud.sh`), the LIDAR USB and GPIO ports, and boot optimization.

## What does not go here

- ROS 2 packages (they go in `src/`).
- Thesis experiments and their results (they go in `experiments/`).
- Installation guides (they go in `docs/robot-setup/`).

## Naming

snake_case with the `.sh` extension. Most scripts in `robot-setup/` explain their usage in their first lines.

## Usage

On the PC, from the workspace root:

```bash
bash scripts/launch/launch_sim_all.sh
```

On the Raspberry Pi, the workspace lives in `~/robot_ws`:

```bash
bash ~/robot_ws/scripts/launch/launch_robot_all.sh
```
