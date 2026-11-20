# scripts

Versión en inglés: [README.en.md](README.en.md)

Scripts para lanzar el sistema y preparar la Raspberry Pi.

## Qué va aquí

- `launch/`: arranque completo del robot real (`launch_robot_all.sh`), de la simulación (`launch_sim_all.sh`) y de las sesiones de mapeo con exploración (`launch_mapeo_all.sh`). Los archivos `mapeo*.txt` guardan los comandos de cada modo.
- `robot-setup/`: diagnóstico y ajustes de la Raspberry Pi, como el estado del sistema (`check_salud.sh`), los puertos USB y GPIO del LIDAR y la optimización del arranque.

## Qué no va aquí

- Paquetes de ROS 2 (van en `src/`).
- Pruebas de la tesis y sus resultados (van en `experiments/`).
- Guías de instalación (van en `docs/robot-setup/`).

## Nombres

snake_case con extensión `.sh`. La mayoría de los scripts de `robot-setup/` explican su uso en las primeras líneas.

## Uso

En el PC, desde la raíz del workspace:

```bash
bash scripts/launch/launch_sim_all.sh
```

En la Raspberry Pi, el workspace está en `~/robot_ws`:

```bash
bash ~/robot_ws/scripts/launch/launch_robot_all.sh
```
