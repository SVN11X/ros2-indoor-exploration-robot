# Thesis paths

The thesis (annex 9, table A9.1) cites code paths relative to `src/`, as the repository was before the reorganization of 2026-11-20. This table maps each cited path to its current location. Every path in the right column exists.

General rules:

- `src/articubot_one/` did not move.
- `src/arduino_firmware/` is now `firmware/`.
- `src/test/` is now `experiments/`.
- `src/prod/` is now `scripts/launch/`.
- `src/diffdrive_arduino/`, `src/gazebo_ros2_control/`, `src/m-explore-ros2/`, `src/serial/` and `src/joy_tester/` are now under `src/third_party/`.

| Path in the thesis | Current path |
| --- | --- |
| `src/articubot_one/description/robot.urdf.xacro` | `src/articubot_one/description/robot.urdf.xacro` |
| `src/articubot_one/description/robot_core.xacro` | `src/articubot_one/description/robot_core.xacro` |
| `src/articubot_one/description/lidar.xacro` | `src/articubot_one/description/lidar.xacro` |
| `src/articubot_one/description/lidar_sim.xacro` | `src/articubot_one/description/lidar_sim.xacro` |
| `src/articubot_one/launch/rplidar.launch.py` | `src/articubot_one/launch/rplidar.launch.py` |
| `src/articubot_one/scripts/rplidar_serial_publisher.py` | `src/articubot_one/scripts/rplidar_serial_publisher.py` |
| `src/articubot_one/description/gazebo_control.xacro` | `src/articubot_one/description/gazebo_control.xacro` |
| `src/articubot_one/description/ros2_control.xacro` | `src/articubot_one/description/ros2_control.xacro` |
| `src/articubot_one/launch/launch_robot.launch.py` | `src/articubot_one/launch/launch_robot.launch.py` |
| `src/articubot_one/launch/launch_sim.launch.py` | `src/articubot_one/launch/launch_sim.launch.py` |
| `src/articubot_one/config/my_controllers.yaml` | `src/articubot_one/config/my_controllers.yaml` |
| `src/articubot_one/config/nav2_params.yaml` | `src/articubot_one/config/nav2_params.yaml` |
| `src/articubot_one/config/nav2_params_sim.yaml` | `src/articubot_one/config/nav2_params_sim.yaml` |
| `src/articubot_one/config/mapper_params_online_async.yaml` | `src/articubot_one/config/mapper_params_online_async.yaml` |
| `src/articubot_one/config/mapper_params_online_async_sim.yaml` | `src/articubot_one/config/mapper_params_online_async_sim.yaml` |
| `src/articubot_one/config/explore.yaml` | `src/articubot_one/config/explore.yaml` |
| `src/articubot_one/worlds/obstacles.world` | `src/articubot_one/worlds/obstacles.world` |
| `src/arduino_firmware/ROSArduinoBridge/ROSArduinoBridge.ino` | `firmware/ROSArduinoBridge/ROSArduinoBridge.ino` |
| `src/arduino_firmware/ROSArduinoBridge/commands.h` | `firmware/ROSArduinoBridge/commands.h` |
| `src/arduino_firmware/ROSArduinoBridge/diff_controller.h` | `firmware/ROSArduinoBridge/diff_controller.h` |
| `src/arduino_firmware/ROSArduinoBridge/encoder_driver.h` | `firmware/ROSArduinoBridge/encoder_driver.h` |
| `src/arduino_firmware/ROSArduinoBridge/encoder_driver.ino` | `firmware/ROSArduinoBridge/encoder_driver.ino` |
| `src/arduino_firmware/ROSArduinoBridge/motor_driver.h` | `firmware/ROSArduinoBridge/motor_driver.h` |
| `src/arduino_firmware/ROSArduinoBridge/motor_driver.ino` | `firmware/ROSArduinoBridge/motor_driver.ino` |
| `src/arduino_firmware/pid_config/ControlLazoAbierto.py` | `firmware/pid_config/ControlLazoAbierto.py` |
| `src/arduino_firmware/pid_config/ControlLazoCerrado.py` | `firmware/pid_config/ControlLazoCerrado.py` |
| `src/arduino_firmware/pid_config/SintonizacionAutomatica.py` | `firmware/pid_config/SintonizacionAutomatica.py` |
| `src/arduino_firmware/pid_config/SintonizacionLambda.py` | `firmware/pid_config/SintonizacionLambda.py` |
| `src/arduino_firmware/pid_config/pyPso.py` | `firmware/pid_config/pyPso.py` |
| `src/arduino_firmware/pid_config/AnalisisEstabilidadPID.py` | `firmware/pid_config/AnalisisEstabilidadPID.py` |
| `src/arduino_firmware/pid_config/resultados_pso.tex` | `firmware/pid_config/resultados_pso.tex` |
| `src/arduino_firmware/pid_config/resultados_lambda.tex` | `firmware/pid_config/resultados_lambda.tex` |
| `src/test/prueba_giro/prueba_giro.py` | `experiments/prueba_giro/prueba_giro.py` |
| `src/test/prueba_giro_sim/prueba_giro_sim.py` | `experiments/prueba_giro_sim/prueba_giro_sim.py` |
| `src/test/exploracion/run_explore.sh` | `experiments/exploracion/run_explore.sh` |
| `src/test/exploracion/clasificar_metas_exploracion.py` | `experiments/exploracion/clasificar_metas_exploracion.py` |
| `src/test/navegacion/run_prueba_nav.sh` | `experiments/navegacion/run_prueba_nav.sh` |
| `src/test/slam/analizar_slam.py` | `experiments/slam/analizar_slam.py` |
| `src/test/mapas_vs_plano/comparar_mapa_plano.py` | `experiments/mapas_vs_plano/comparar_mapa_plano.py` |
| `src/test/mapas_vs_plano/resultados_comparacion_plano.txt` | `experiments/mapas_vs_plano/resultados_comparacion_plano.txt` |
| `src/test/sesiones_mapeo/` | `experiments/sesiones_mapeo/` |
