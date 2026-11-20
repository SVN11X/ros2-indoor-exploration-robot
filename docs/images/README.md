# images

Versión en inglés: [README.en.md](README.en.md)

Fotos y capturas del proyecto, ordenadas por tema. Los gráficos de resultados no están aquí: los generan los scripts y quedan junto a su prueba en `experiments/` y en `firmware/pid_config/`.

## Qué va aquí

- `robot/`: fotos del prototipo.
- `field-tests/`: fotos de las pruebas en el robot real.
- `simulation/`: Gazebo y RViz con el gemelo digital.
- `real-robot/`: RViz durante el mapeo y la navegación del robot real.

Las capturas de las guías de instalación van junto a su guía, en `docs/robot-setup/`.

## Nombres

kebab-case en inglés, describiendo lo que se ve. Si hay varias del mismo tipo, terminan en la fecha `AAAA-MM-DD` o en un número.

## Robot

| | |
| --- | --- |
| <img src="robot/robot-front.jpg" width="200" alt="Vista frontal del robot"> | <img src="robot/robot-front-left.jpg" width="200" alt="Vista diagonal del robot"> |
| Vista frontal, con la cámara al centro y el LIDAR arriba. | Vista diagonal. |
| <img src="robot/robot-side.jpg" width="200" alt="Vista lateral del robot"> | <img src="robot/robot-top.jpg" width="200" alt="Vista superior del robot"> |
| Vista lateral. | Vista superior, con el LIDAR y el medidor de voltaje, corriente y potencia. |

## Pruebas de campo

Pruebas de odometría en el robot real, sobre alfombra, con cinta como referencia (25 de marzo de 2026). Los resultados están en `experiments/linea_recta/` y `experiments/prueba_giro/`.

| | |
| --- | --- |
| <img src="field-tests/odometry-test-robot-on-marks-1.jpg" width="200" alt="Robot junto a las marcas de la prueba"> | <img src="field-tests/odometry-test-robot-on-marks-2.jpg" width="200" alt="Robot junto a las marcas, otra vista"> |
| Robot junto a las marcas de la prueba. | La misma posición, vista desde el otro lado. |
| <img src="field-tests/odometry-test-marks.jpg" width="200" alt="Marcas numeradas en el piso"> | <img src="field-tests/odometry-test-reference-line.jpg" width="200" alt="Línea de cinta de referencia"> |
| Marcas numeradas de cada repetición. | Línea de cinta usada como referencia. |

## Simulación

| | |
| --- | --- |
| <img src="simulation/gazebo-obstacles-world.jpg" width="360" alt="Mundo de prueba en Gazebo"> | <img src="simulation/obstacles-world-layout.png" width="300" alt="Plano del mundo de prueba"> |
| Mundo de prueba con obstáculos en Gazebo Classic. | Plano del mundo: 6 m por 8 m, cajas B1 a B8 y cilindros C1 a C6. |
| <img src="simulation/rviz-robot-model.png" width="360" alt="Modelo del robot en RViz"> | <img src="simulation/rviz-simulated-lidar-scan.png" width="360" alt="Barrido del LIDAR simulado"> |
| Modelo URDF del robot en RViz. | Puntos del LIDAR simulado. |
| <img src="simulation/mapping-rviz-and-gazebo.png" width="360" alt="Mapeo en RViz y Gazebo"> | <img src="simulation/mapping-start.png" width="360" alt="Inicio del mapeo"> |
| Mapeo en simulación: RViz a la izquierda y Gazebo a la derecha. | Inicio del mapeo con los primeros barridos. |
| <img src="simulation/mapping-costmap-progress.png" width="360" alt="Mapa de costos durante el mapeo"> | <img src="simulation/nav2-goal-pose.png" width="360" alt="Meta de navegación"> |
| Mapa de costos durante el mapeo. | Meta de navegación fijada con 2D Goal Pose. |
| <img src="simulation/straight-path-in-rviz.png" width="360" alt="Trayectoria recta en RViz"> | <img src="simulation/robot-footprint-on-costmap.png" width="360" alt="Huella del robot en el mapa de costos"> |
| Trayectoria recta registrada en RViz. | Huella del robot sobre el mapa de costos. |
| <img src="simulation/exploration-early-scan.png" width="360" alt="Comienzo de la exploración"> | <img src="simulation/exploration-inflated-obstacles.png" width="360" alt="Obstáculos inflados"> |
| Comienzo de la exploración por fronteras. | Zona de seguridad alrededor de los cilindros. |
| <img src="simulation/exploration-costmap.png" width="360" alt="Mapa de costos durante la exploración"> | <img src="simulation/exploration-map-overview.png" width="360" alt="Vista general del mapa explorado"> |
| Mapa de costos durante la exploración. | Vista general del mapa explorado. |

## Robot real

| | |
| --- | --- |
| <img src="real-robot/mapping-apartment-2026-01-01.png" width="360" alt="Mapa de una habitación"> | <img src="real-robot/navigation-planned-path-2026-01-16.png" width="360" alt="Ruta planificada por Nav2"> |
| Mapa de una habitación con su mapa de costos (1 de enero de 2026). | Ruta planificada por Nav2 con los barridos del LIDAR (16 de enero). |
| <img src="real-robot/mapping-corridor-2026-01-17-1.png" width="360" alt="Mapeo de un pasillo, 1"> | <img src="real-robot/mapping-corridor-2026-01-17-2.png" width="360" alt="Mapeo de un pasillo, 2"> |
| Mapeo de un pasillo, captura 1 (17 de enero). | Captura 2, el mismo día. |
| <img src="real-robot/mapping-corridor-2026-01-17-3.png" width="360" alt="Mapeo de un pasillo, 3"> | <img src="real-robot/mapping-corridor-2026-01-17-4.png" width="360" alt="Mapeo de un pasillo, 4"> |
| Captura 3. | Captura 4. |
| <img src="real-robot/mapping-room-annotated-2026-01-24.png" width="360" alt="Mapa de una sala con zonas marcadas"> | <img src="real-robot/navigation-room-path-2026-01-24.png" width="360" alt="Ruta de navegación en la sala"> |
| Mapa de una sala con dos zonas marcadas a mano (24 de enero). | Ruta de navegación en la misma sala. |
| <img src="real-robot/odom-topic-rate-30hz.png" width="200" alt="Frecuencia del tópico odom"> | |
| `ros2 topic hz /odom`: la odometría se publica a unos 30 Hz. | |

Los videos de las pruebas están en [docs/videos/](../videos/README.md).
