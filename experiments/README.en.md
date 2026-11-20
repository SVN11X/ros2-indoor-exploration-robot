# experiments

Spanish version: [README.md](README.md)

Field and simulation experiments of the thesis, with their scripts and recorded results.

## What goes here

- One folder per experiment, for example `prueba_giro/` (real robot) and `prueba_giro_sim/` (Gazebo).
- In each folder, the script that runs the experiment (`run_*.sh`), the one that analyzes it (`analizar_*.py`) and the results the thesis cites.
- `sesiones_mapeo/`: copies of each mapping and exploration session. The `.posegraph` and `*_slam_replay.log` files are stored in Git LFS.
- `utils/`, `recursos/` and `check/`: tools shared by several experiments.
- `requirements.txt` and `setup_test_env.sh`: Python dependencies of the analysis scripts.

## What does not go here

- ROS 2 packages (they go in `src/`).
- Scripts that launch the robot or the simulation (they go in `scripts/launch/`).
- Automated tests that run without the robot or Gazebo (they would go in `tests/`).

## Naming

Folders in snake_case and in Spanish, as the thesis cites them. The `_sim` suffix marks the simulation version of an experiment.

## Usage

From the workspace root, after `colcon build` and with the robot or the simulation running:

```bash
bash experiments/prueba_giro/run_prueba_giro.sh
```

The thesis cites these paths as `src/test/...`. The mapping table is in `docs/thesis-paths.md`.
