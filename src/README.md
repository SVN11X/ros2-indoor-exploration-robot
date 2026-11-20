# src

Versión en inglés: [README.en.md](README.en.md)

Paquetes de ROS 2 del workspace. colcon los busca en cualquier nivel dentro de esta carpeta.

## Qué va aquí

- `articubot_one/`: modelo URDF y xacro del robot, archivos launch y parámetros de control, SLAM, Nav2, exploración y simulación.
- `serial_motor_demo/`: paquete de prueba de motores por puerto serie y sus mensajes.
- `third_party/`: paquetes que vienen de otros proyectos. Su origen y licencia están en `docs/credits.md`.

## Qué no va aquí

- Firmware del Arduino (va en `firmware/`).
- Scripts de arranque (van en `scripts/launch/`).
- Pruebas de la tesis y sus resultados (van en `experiments/`).
- Salidas de colcon (`build/`, `install/` y `log/` quedan en la raíz y están ignoradas).

## Nombres

Cada paquete usa el nombre que declara su `package.xml`, en snake_case.
