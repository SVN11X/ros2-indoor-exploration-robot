# images

Versión en inglés: [README.en.md](README.en.md)

Fotos y capturas del proyecto, ordenadas por tema. Los gráficos de resultados no están aquí: los generan los scripts y quedan junto a su prueba en `experiments/` y en `firmware/pid_config/`.

## Qué va aquí

- `robot/`: fotos del prototipo.
- `field-tests/`: fotos de las pruebas en el robot real.
- `simulation/`: Gazebo y RViz con el gemelo digital.
- `real-robot/`: RViz durante el mapeo y la navegación del robot real.
- `mechanical/`: imágenes de los modelos 3D de `mechanical/`, generadas desde sus archivos STEP, y renders de Fusion 360.
- `diagrams/`: diagramas de la tesis con su PowerPoint de origen, y los árboles TF en PDF.
- `components/`: fotos de los componentes, de tiendas o fabricantes.

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
| <img src="robot/robot-front-close.jpg" width="200" alt="Vista frontal del robot, más cerca"> | <img src="robot/robot-right-side-close.jpg" width="200" alt="Vista lateral derecha del robot"> |
| Vista frontal, más cerca. | Vista lateral derecha, más cerca. |
| <img src="robot/robot-front-right-close.png" width="200" alt="Vista frontal y lateral derecha del robot"> |  |
| Vista frontal y lateral derecha, más cerca. |  |

## Modelos 3D

Los modelos están en [mechanical/](../../mechanical/README.md). Las imágenes con componentes usan los mismos números.

| | |
| --- | --- |
| <img src="mechanical/robot-v2.png" width="200" alt="Modelo 3D del robot construido"> | <img src="mechanical/robot-v2-inside.png" width="200" alt="Interior del modelo 3D con los componentes numerados"> |
| El robot construido (v2). | El interior de v2 con los componentes numerados. |
| <img src="mechanical/robot-v1.png" width="200" alt="Primer diseño del chasis"> | <img src="mechanical/motor-control-stack.png" width="200" alt="Arduino Nano, placa de bornes y driver L298N"> |
| Primer diseño del chasis (v1). | El Arduino Nano, su placa de bornes y el driver L298N. |
| <img src="mechanical/components.png" width="200" alt="Los 11 modelos de componentes"> | |
| Los 11 modelos de componentes, con el nombre de su archivo. | |
| <img src="mechanical/robot-v2-render-top-left-front.png" width="200" alt="Render de Fusion 360 de v2, vista superior izquierda, frente"> | <img src="mechanical/robot-v2-render-top-left-back.png" width="200" alt="Render de Fusion 360 de v2, vista superior izquierda, parte trasera"> |
| Render de Fusion 360 de v2. Vista superior izquierda, frente. | Render de Fusion 360 de v2. Vista superior izquierda, parte trasera. |
| <img src="mechanical/robot-v2-render-top-right.png" width="200" alt="Render de Fusion 360 de v2, vista superior derecha"> | <img src="mechanical/robot-v2-render-bottom-right.png" width="200" alt="Render de Fusion 360 de v2, vista inferior derecha"> |
| Render de Fusion 360 de v2. Vista superior derecha. | Render de Fusion 360 de v2. Vista inferior derecha. |

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
| <img src="simulation/gazebo-scenario-overview.jpg" width="360" alt="Escenario visual de Gazebo con personas, postes y un bloque numerado"> | <img src="simulation/gazebo-scenario-close.jpg" width="360" alt="El mismo escenario, más cerca del robot"> |
| Escenario visual de Gazebo con personas, postes y un bloque numerado. | El mismo escenario, más cerca del robot. |
| <img src="simulation/gazebo-camera-view.jpg" width="360" alt="Campo de visión de la cámara simulada"> | <img src="simulation/rviz-lidar-scan-obstacles.png" width="360" alt="Barrido del LIDAR simulado sobre los obstáculos, en RViz"> |
| Campo de visión de la cámara simulada. | Barrido del LIDAR simulado sobre los obstáculos, en RViz. |
| <img src="simulation/rviz-costmap-scan.png" width="360" alt="Mapa de costos y barrido del LIDAR en RViz"> | <img src="simulation/rviz-tf-frames.png" width="360" alt="Ejes de los marcos TF del robot en RViz"> |
| Mapa de costos y barrido del LIDAR en RViz. | Ejes de los marcos TF del robot en RViz. |
| <img src="simulation/navigation-sample-1.png" width="360" alt="Navegación en simulación, Gazebo a la izquierda y RViz a la derecha, momento 1"> | <img src="simulation/navigation-sample-2.png" width="360" alt="Momento 2"> |
| Navegación en simulación, Gazebo a la izquierda y RViz a la derecha, momento 1. | Momento 2. |
| <img src="simulation/navigation-sample-3.png" width="360" alt="Momento 3"> |  |
| Momento 3. |  |

Las pruebas de odometría en Gazebo están en [experiments/](../../experiments/README.md#odometría).

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

## Diagramas

Figuras de la tesis. Cada PNG tiene al lado su PowerPoint de origen, con el mismo nombre y extensión `.pptx`. Los README de cada carpeta las muestran donde explican algo.

- General: [gemelo digital](diagrams/digital-twin-sync.png), [repositorio en el PC y en el robot](diagrams/workspace-folders.png), [conexiones eléctricas](diagrams/wiring-diagram.png) y [consumo de potencia](diagrams/power-budget.png).
- Firmware: [archivos](diagrams/firmware-file-tree.png), [arquitectura](diagrams/firmware-architecture.png), [arranque](diagrams/firmware-startup-sequence.png), [ciclo de control](diagrams/firmware-control-sequence.png), [conversión de unidades](diagrams/ros2-control-unit-conversion.png) y [estados del encoder](diagrams/encoder-quadrature-states.jpg).
- ROS 2: [archivos xacro](diagrams/xacro-file-structure.png), [elección entre robot real y simulación](diagrams/xacro-decision-tree.png), [de xacro a /tf](diagrams/urdf-to-tf-flow.png), [orden de arranque](diagrams/launch-startup-sequence.png), [control diferencial](diagrams/differential-control-flow.png), [plugin diferencial de Gazebo](diagrams/gazebo-diff-drive-plugin.png), [árbol de comportamiento de Nav2](diagrams/nav2-behavior-tree.png) y [nodos y tópicos en ejecución](diagrams/ros-graph.png).
- Validación: [validación del gemelo digital](diagrams/validation-flowchart.png), y los árboles TF de la [simulación](diagrams/tf-tree-simulation.pdf) y del [robot real](diagrams/tf-tree-real-robot.pdf).

La mayoría tiene fondo transparente y texto oscuro, así que se lee mejor con el tema claro de GitHub.

## Componentes

Fotos de tiendas o fabricantes. Su origen no está registrado, como dice `docs/credits.md`.

|  |  |  |
| --- | --- | --- |
| <img src="components/rplidar-a1m8.jpg" width="140" alt="RPLidar A1M8"> | <img src="components/arduino-nano.jpg" width="140" alt="Arduino Nano"> | <img src="components/l298n-driver.png" width="140" alt="Driver L298N"> |
| RPLidar A1M8 | Arduino Nano | Driver L298N |
| <img src="components/jga25-370-motor.jpg" width="140" alt="Motorreductor JGA25-370"> | <img src="components/motor-encoder-pinout.jpg" width="140" alt="Cables del motor con encoder"> | <img src="components/wheels.png" width="140" alt="Ruedas"> |
| Motorreductor JGA25-370 | Cables del motor con encoder | Ruedas |
| <img src="components/ball-caster.png" width="140" alt="Rueda loca"> | <img src="components/battery.png" width="140" alt="Batería de 12 V"> | <img src="components/dc-dc-power-module.jpg" width="140" alt="Módulo reductor DC-DC DFRobot DFR0205"> |
| Rueda loca | Batería de 12 V | Módulo reductor DC-DC DFRobot DFR0205 |
| <img src="components/raspberry-pi-camera.jpg" width="140" alt="Cámara Raspberry Pi"> | <img src="components/power-switch.jpg" width="140" alt="Interruptor"> | <img src="components/blade-fuse.jpg" width="140" alt="Fusible"> |
| Cámara Raspberry Pi | Interruptor | Fusible |
| <img src="components/travel-router.png" width="140" alt="Router de viaje GL.iNet GL-MT300N-V2"> | <img src="components/pla-plus-filament.png" width="140" alt="Filamento PLA+"> | <img src="components/ender-3-printer.jpg" width="140" alt="Impresora 3D Ender 3"> |
| Router de viaje GL.iNet GL-MT300N-V2 | Filamento PLA+ | Impresora 3D Ender 3 |
