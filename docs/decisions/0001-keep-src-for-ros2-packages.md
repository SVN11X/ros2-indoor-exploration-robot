# 0001. Keep src/ for ROS 2 packages only

- Status: accepted
- Date: 2026-11-20
- Proposed by: Claude Code
- Accepted by: owner, in the Claude Code session of 2026-11-20 ("Orden completo")

## Context

The repository root is a colcon workspace. Before this change, `src/` mixed ROS 2 packages with the Arduino firmware, the launch scripts and the thesis experiments with their recorded data. The thesis (annex 9) cites code paths relative to `src/`, and about 40 lines of shell scripts depend on those locations, on the PC (`~/tesis_black_robot`) and on the Raspberry Pi (`~/robot_ws`).

## Decision

- `src/` keeps only ROS 2 packages. Packages from other projects go to `src/third_party/`.
- `src/arduino_firmware/` becomes `firmware/`.
- `src/test/` becomes `experiments/`.
- `src/prod/` becomes `scripts/launch/`, and the Raspberry Pi setup scripts go to `scripts/robot-setup/`.
- Only the paths a move breaks change in code: 17 lines for `experiments/`, 4 usage messages for `scripts/launch/`, and 2 location comments in `firmware/pid_config/`.
- `docs/thesis-paths.md` maps every path the thesis cites to its new location.

## Alternatives considered

- Leave `src/` as it was and move only documentation. No code changes and the thesis paths stay valid, but the colcon source tree keeps holding data and non-ROS code.
- Move everything and also rename folders to English. More changes in code and a larger gap with the thesis.

## Consequences

- colcon only scans ROS 2 packages, and each top-level folder has one purpose.
- The thesis paths no longer match the repository. `docs/thesis-paths.md` closes that gap.
- The PC and the Raspberry Pi need `git pull` and a clean build (`rm -rf build install log`).
- To undo it, revert the refactor commits of pull request #1.
