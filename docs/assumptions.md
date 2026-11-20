# Assumptions

Things taken as true without confirmation. Review the open ones in every pull request. Status is open, confirmed or discarded.

| Date | Assumption | Made by | Task | Status |
|------|------------|---------|------|--------|
| 2026-11-20 | The Raspberry Pi gets the new layout by pulling the repository into `~/robot_ws`. | Claude Code | Order folders (PR #1) | open |
| 2026-11-20 | `~/robot_ws/test/recursos/` and `~/tesis_black_robot/test/recursos/`, used by `launch_mapeo_all.sh`, `monitor_pi.sh` and `monitor_sim.sh`, are folders outside the repository, so they stay unchanged. | Claude Code | Order folders (PR #1) | open |
| 2026-11-20 | `src/serial_motor_demo/` comes from joshnewans/serial_motor_demo, as its README and the firmware README suggest. | Claude Code | Order folders (PR #1) | open |
