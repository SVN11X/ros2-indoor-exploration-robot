#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
import time
import shutil
from typing import Optional

def parse_args():
    p = argparse.ArgumentParser(
        description='Guarda el mapa ROS 2 activo en disco (3 métodos con fallback).'
    )
    p.add_argument('--destino',    required=True,
                   help='Directorio de salida (se crea si no existe)')
    p.add_argument('--nombre',     required=True,
                   help='Nombre base del archivo sin extensión (ej: mapa_sim)')
    p.add_argument('--modo',       default='sim', choices=['sim', 'real'],
                   help='Entorno de prueba: sim o real (se pasa a analizar_slam.py)')
    p.add_argument('--bag',        default='',
                   help='Ruta al directorio del rosbag para analizar_slam.py')
    p.add_argument('--slam-pid',   type=int, default=0,
                   help='PID del proceso slam_toolbox (para verificar que sigue vivo)')
    p.add_argument('--ws',         default=os.path.expanduser('~/tesis_black_robot'),
                   help='Raíz del workspace ROS 2')
    p.add_argument('--no-analizar', action='store_true',
                   help='Omitir analizar_slam.py aunque se proporcione --bag')
    return p.parse_args()

def guardar_con_rclpy(pgm_path: str) -> bool:

    try:
        import rclpy
        from rclpy.node import Node
        from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
        from nav_msgs.msg import OccupancyGrid

        class _MapSaver(Node):
            def __init__(self):
                super().__init__('map_saver_guardar_mapa')
                self.saved = False
                qos = QoSProfile(
                    depth=1,
                    durability=DurabilityPolicy.TRANSIENT_LOCAL,
                    reliability=ReliabilityPolicy.RELIABLE,
                )
                self.create_subscription(OccupancyGrid, '/map', self._cb, qos)

            def _cb(self, msg):
                if self.saved:
                    return
                w, h = msg.info.width, msg.info.height
                raw = list(msg.data)
                rows = []
                for i in range(h):
                    row = bytes(
                        205 if v == -1 else (0 if v > 50 else 254)
                        for v in raw[i * w:(i + 1) * w]
                    )
                    rows.append(row)
                with open(pgm_path, 'wb') as f:
                    f.write(f'P5\n{w} {h}\n255\n'.encode())
                    for row in reversed(rows):
                        f.write(row)

                yaml_path = pgm_path.replace('.pgm', '.yaml')
                res = msg.info.resolution
                ox  = msg.info.origin.position.x
                oy  = msg.info.origin.position.y
                with open(yaml_path, 'w') as f:
                    f.write(f'image: {pgm_path}\n')
                    f.write(f'resolution: {res}\n')
                    f.write(f'origin: [{ox}, {oy}, 0.0]\n')
                    f.write('negate: 0\noccupied_thresh: 0.65\nfree_thresh: 0.25\n')
                self.saved = True

        rclpy.init()
        node = _MapSaver()
        t0 = time.time()
        while not node.saved and (time.time() - t0) < 10:
            rclpy.spin_once(node, timeout_sec=0.5)
        success = node.saved
        node.destroy_node()
        rclpy.shutdown()
        return success

    except Exception as e:
        print(f'    rclpy: {e}')
        return False

def guardar_con_service(destino_base: str) -> bool:
    try:
        r = subprocess.run(
            [
                'ros2', 'service', 'call',
                '/slam_toolbox/save_map',
                'slam_toolbox/srv/SaveMap',
                f"{{name: {{data: '{destino_base}'}}}}",
            ],
            capture_output=True, timeout=15,
        )
        return r.returncode == 0
    except Exception as e:
        print(f'    slam_toolbox service: {e}')
        return False

def guardar_con_map_saver(destino_base: str) -> bool:
    try:
        r = subprocess.run(
            [
                'ros2', 'run', 'nav2_map_server', 'map_saver_cli',
                '-f', destino_base,
                '--ros-args', '-p', 'save_map_timeout:=5.0',
            ],
            capture_output=True, timeout=20,
        )
        return r.returncode == 0
    except Exception as e:
        print(f'    map_saver_cli: {e}')
        return False

def convertir_png(pgm_path: str) -> Optional[str]:
    png_path = pgm_path.replace('.pgm', '.png')
    if shutil.which('convert'):
        try:
            subprocess.run(['convert', pgm_path, png_path],
                           capture_output=True, timeout=10)
            if os.path.exists(png_path):
                print(f'  ✓ PNG: {png_path}')
                return png_path
        except Exception as e:
            print(f'  AVISO PNG: {e}')
    return None

def run_analizar_slam(ws: str, bag: str, pgm: str,
                      modo: str, destino: str, nombre: str) -> None:
    analizar = os.path.join(ws, 'src', 'test', 'slam', 'analizar_slam.py')
    if not os.path.exists(analizar):
        print(f'  AVISO: analizar_slam.py no encontrado en {analizar}')
        return
    # Sin versionamiento: análisis SLAM con sufijo fijo por modo.
    suffix = modo

    cmd = [
        'python3', analizar,
        '--bag',    bag,
        '--pgm',    pgm,
        '--modo',   modo,
        '--suffix', suffix,
        '--out',    destino,
    ]
    print(f'  Ejecutando analizar_slam.py ({modo})...')
    r = subprocess.run(cmd)
    if r.returncode == 0:
        print(f'  ✓ Análisis SLAM guardado en {destino}')
    else:
        print(f'  AVISO: analizar_slam.py terminó con código {r.returncode}')

def main():
    args = parse_args()

    os.makedirs(args.destino, exist_ok=True)
    pgm_path     = os.path.join(args.destino, args.nombre + '.pgm')
    destino_base = os.path.join(args.destino, args.nombre)

    print(f'\n{"═"*54}')
    print(f'  Guardando mapa ({args.modo})')
    print(f'  Destino: {pgm_path}')
    print(f'{"═"*54}')
    if args.slam_pid:
        try:
            os.kill(args.slam_pid, 0)
            print(f'  ✓ slam_toolbox vivo (PID {args.slam_pid})')
        except ProcessLookupError:
            print(f'  ✗ slam_toolbox (PID {args.slam_pid}) ya no existe')
            print(f'    El mapa retenido puede no estar disponible.')

    saved = False
    print('  [1/3] rclpy TRANSIENT_LOCAL QoS...')
    if guardar_con_rclpy(pgm_path) and os.path.exists(pgm_path):
        print('  ✓ Método 1 exitoso')
        saved = True
    if not saved:
        print('  [2/3] ros2 service /slam_toolbox/save_map...')
        if guardar_con_service(destino_base) and os.path.exists(pgm_path):
            print('  ✓ Método 2 exitoso')
            saved = True
    if not saved:
        print('  [3/3] map_saver_cli (fallback final)...')
        if guardar_con_map_saver(destino_base) and os.path.exists(pgm_path):
            print('  ✓ Método 3 exitoso')
            saved = True

    if not saved:
        print('\n  ✗ No se pudo guardar el mapa con ningún método.')
        print(f'  Comando manual mientras ROS esté activo:')
        print(f'    ros2 run nav2_map_server map_saver_cli -f {destino_base}')
        sys.exit(1)
    convertir_png(pgm_path)
    if not args.no_analizar and args.bag:
        if os.path.exists(args.bag):
            run_analizar_slam(
                args.ws, args.bag, pgm_path,
                args.modo, args.destino, args.nombre,
            )
        else:
            print(f'  AVISO: bag no encontrado en {args.bag}, saltando análisis')

    print(f'\n  ✓ Mapa listo: {pgm_path}')
    sys.exit(0)

if __name__ == '__main__':
    main()