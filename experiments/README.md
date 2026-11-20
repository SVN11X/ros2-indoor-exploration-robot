# experiments

Versión en inglés: [README.en.md](README.en.md)

Pruebas de campo y de simulación de la tesis, con sus scripts y sus resultados registrados.

## Qué va aquí

- Una carpeta por prueba, por ejemplo `prueba_giro/` (robot real) y `prueba_giro_sim/` (Gazebo).
- En cada carpeta, el script que ejecuta la prueba (`run_*.sh`), el que la analiza (`analizar_*.py`) y los resultados que cita la tesis.
- `sesiones_mapeo/`: copias de cada sesión de mapeo y exploración. Los archivos `.posegraph` y `*_slam_replay.log` están en Git LFS.
- `utils/`, `recursos/` y `check/`: herramientas que comparten varias pruebas.
- `requirements.txt` y `setup_test_env.sh`: dependencias de Python de los análisis.

## Qué no va aquí

- Paquetes de ROS 2 (van en `src/`).
- Scripts para lanzar el robot o la simulación (van en `scripts/launch/`).
- Pruebas automáticas que corren sin robot ni Gazebo (irían en `tests/`).

## Nombres

Carpetas en snake_case y en español, como las cita la tesis. El sufijo `_sim` indica la versión en simulación de una prueba.

## Uso

Desde la raíz del workspace, después de `colcon build` y con el robot o la simulación en marcha:

```bash
bash experiments/prueba_giro/run_prueba_giro.sh
```

La tesis cita estas rutas como `src/test/...`. La tabla de equivalencias está en `docs/thesis-paths.md`.
