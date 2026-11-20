#!/usr/bin/env python3
import sys
import os
import glob
import argparse
import csv
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

plt.rcParams.update({'font.size': 10, 'axes.grid': False, 'figure.dpi': 150})

def encontrar_raiz_workspace():

    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidate = script_dir
    for _ in range(6):
        if os.path.isdir(os.path.join(candidate, 'src', 'articubot_one')):
            return candidate
        if os.path.isdir(os.path.join(candidate, 'install')) and \
           os.path.isdir(os.path.join(candidate, 'src')):
            return candidate
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent
    return None

def encontrar_bag_mas_reciente(ws_root, modo):

    prefijo = f"mapeo_{modo}"
    base_bags = os.path.join(ws_root, 'src', 'test', 'slam', prefijo)

    if not os.path.isdir(base_bags):
        return None
    # Modo sin versionamiento: el bag puede quedar directamente en base_bags.
    if os.path.exists(os.path.join(base_bags, 'metadata.yaml')) or glob.glob(os.path.join(base_bags, '*.db3')):
        return base_bags

    carpetas = sorted([
        os.path.join(base_bags, d)
        for d in os.listdir(base_bags)
        if os.path.isdir(os.path.join(base_bags, d))
        and d.startswith(prefijo + '_')
    ])
    return carpetas[-1] if carpetas else None

def encontrar_pgm_mas_reciente(ws_root, modo):

    prefijo_mapa = f"mapa_{modo}_"
    base_maps = os.path.join(ws_root, 'src', 'articubot_one', 'maps', f'map_{modo}')

    if not os.path.isdir(base_maps):
        return None

    # Modo sin versionamiento: prioriza nombre fijo.
    fijo = os.path.join(base_maps, f'mapa_{modo}.pgm')
    if os.path.exists(fijo):
        return fijo

    patron = os.path.join(base_maps, '**', f'{prefijo_mapa}*.pgm')
    pgms = sorted(glob.glob(patron, recursive=True))
    return pgms[-1] if pgms else None

def autodescubrir(modo):

    ws = encontrar_raiz_workspace()
    if ws is None:
        return None, None, None

    bag  = encontrar_bag_mas_reciente(ws, modo)
    pgm  = encontrar_pgm_mas_reciente(ws, modo)
    out  = os.path.dirname(pgm) if pgm else '.'

    return bag, pgm, out

def mostrar_descubrimiento(modo, bag, pgm, out):

    print(f"\n{'─'*60}")
    print(f"  Auto-descubrimiento — modo: {modo}")
    print(f"{'─'*60}")
    print(f"  Bag  : {bag  or '⚠  no encontrado'}")
    print(f"  PGM  : {pgm  or '⚠  no encontrado'}")
    print(f"  Out  : {out}")
    print(f"{'─'*60}\n")

def leer_odom_bag(bag_path):

    try:
        import rosbag2_py
        from rclpy.serialization import deserialize_message
        from nav_msgs.msg import Odometry
    except ImportError:
        print("  AVISO: rosbag2_py no disponible.")
        print("  Requiere entorno ROS 2 activo (source install/setup.bash).")
        print("  Continuando sin datos de trayectoria...\n")
        return None, None, None

    storage_id = 'sqlite3'
    if os.path.isdir(bag_path) and any(
            f.endswith('.mcap') for f in os.listdir(bag_path)):
        storage_id = 'mcap'

    storage_options  = rosbag2_py.StorageOptions(uri=bag_path, storage_id=storage_id)
    converter_options = rosbag2_py.ConverterOptions(
        input_serialization_format='cdr',
        output_serialization_format='cdr')

    reader = rosbag2_py.SequentialReader()
    try:
        reader.open(storage_options, converter_options)
    except Exception as e:
        print(f"  ERROR abriendo bag: {e}")
        return None, None, None

    reader.set_filter(rosbag2_py.StorageFilter(topics=['/odom']))

    times, xs, ys = [], [], []
    while reader.has_next():
        _, data, stamp = reader.read_next()
        try:
            msg = deserialize_message(data, Odometry)
            times.append(stamp / 1e9)
            xs.append(msg.pose.pose.position.x)
            ys.append(msg.pose.pose.position.y)
        except Exception:
            continue

    if not times:
        print("  AVISO: No se encontraron mensajes /odom en el bag.")
        return None, None, None

    return np.array(times), np.array(xs), np.array(ys)

def calcular_distancia(xs, ys):
    xs = np.array(xs)
    ys = np.array(ys)
    mask = np.isfinite(xs) & np.isfinite(ys)
    xs_clean = xs[mask]
    ys_clean = ys[mask]

    if len(xs_clean) < 2:
        return 0.0

    dx = np.diff(xs_clean)
    dy = np.diff(ys_clean)
    dist = float(np.sum(np.sqrt(dx**2 + dy**2)))

    return dist

def _decode_odom_xy_cdr(data: bytes):

    import struct
    offset = 4
    offset += 8
    if offset + 4 > len(data):
        raise ValueError("datos insuficientes para frame_id")
    str_len = struct.unpack_from('<I', data, offset)[0]
    offset += 4 + str_len
    rem = offset % 4
    if rem:
        offset += 4 - rem
    if offset + 4 > len(data):
        raise ValueError("datos insuficientes para child_frame_id")
    str_len = struct.unpack_from('<I', data, offset)[0]
    offset += 4 + str_len
    rem = offset % 4
    if rem:
        offset += 4 - rem
    rem = offset % 8
    if rem:
        offset += 8 - rem

    if offset + 16 > len(data):
        raise ValueError("datos insuficientes para position.x,y")

    x = struct.unpack_from('<d', data, offset)[0]
    y = struct.unpack_from('<d', data, offset + 8)[0]

    if abs(x) > 10_000 or abs(y) > 10_000:
        raise ValueError(f"coordenadas fuera de rango: ({x:.1f}, {y:.1f})")

    return x, y

def leer_odom_bag_rosbags(bag_path):

    try:
        from rosbags.rosbag2 import Reader
        from rosbags.typesys import get_typestore, Stores
    except ImportError:
        print("  AVISO: rosbags no instalado. Ejecutar: pip install rosbags")
        return None, None, None

    try:
        typestore = get_typestore(Stores.ROS2_FOXY)

        times, xs, ys = [], [], []
        with Reader(bag_path) as reader:
            connections = [conn for conn in reader.connections if conn.topic == '/odom']

            for connection, timestamp, rawdata in reader.messages(connections=connections):
                msg = typestore.deserialize_cdr(rawdata, connection.msgtype)
                times.append(timestamp / 1e9)
                xs.append(msg.pose.pose.position.x)
                ys.append(msg.pose.pose.position.y)

        if not times:
            print("  AVISO: No se encontraron mensajes /odom")
            return None, None, None

        print(f"    Mensajes /odom leídos (rosbags): {len(times)}")
        return np.array(times), np.array(xs), np.array(ys)

    except Exception as e:
        print(f"  ERROR con rosbags: {e}")
        return None, None, None

def leer_odom_bag_sqlite(bag_path):

    import sqlite3 as _sqlite3
    import struct
    try:
        db3_files = [f for f in os.listdir(bag_path) if f.endswith('.db3')]
    except Exception as e:
        print(f"  ERROR listando bag: {e}")
        return None, None, None

    if not db3_files:
        print("  AVISO: no se encontró .db3 en el bag")
        return None, None, None

    db3_path = os.path.join(bag_path, db3_files[0])

    try:
        conn = _sqlite3.connect(db3_path)
        cur  = conn.cursor()
        cur.execute("SELECT id FROM topics WHERE name = '/odom'")
        row = cur.fetchone()
        if not row:
            print("  AVISO: /odom no encontrado en el bag")
            conn.close()
            return None, None, None
        odom_id = row[0]
        cur.execute(
            "SELECT timestamp, data FROM messages WHERE topic_id = ? ORDER BY timestamp",
            (odom_id,)
        )
        rows = cur.fetchall()
        conn.close()

    except Exception as e:
        print(f"  ERROR leyendo .db3: {e}")
        return None, None, None

    if not rows:
        print("  AVISO: bag sin mensajes /odom")
        return None, None, None

    times, xs, ys = [], [], []
    errores = 0
    for timestamp, data in rows:
        try:
            x, y = _decode_odom_xy_cdr(bytes(data))
            times.append(timestamp / 1e9)
            xs.append(x)
            ys.append(y)
        except Exception:
            errores += 1
            continue

    if errores > 0:
        print(f"  AVISO: {errores}/{len(rows)} mensajes /odom no decodificados")

    if not times:
        print("  AVISO: ningún mensaje /odom pudo decodificarse")
        return None, None, None

    print(f"    Mensajes /odom leídos (sqlite3): {len(times)}")
    return np.array(times), np.array(xs), np.array(ys)

def leer_metadata_bag(bag_path):

    metadata_path = os.path.join(bag_path, 'metadata.yaml')
    if not os.path.exists(metadata_path):
        return None, None

    duracion_s = None
    n_odom = None
    try:
        with open(metadata_path) as f:
            contenido = f.read()
        import re
        m = re.search(r'duration:\s*\n\s*nanoseconds:\s*(\d+)', contenido)
        if m:
            duracion_s = int(m.group(1)) / 1e9
        odom_match = re.search(
            r'name:\s*/odom.*?message_count:\s*(\d+)',
            contenido, re.DOTALL)
        if odom_match:
            n_odom = int(odom_match.group(1))

    except Exception as e:
        print(f"  AVISO: No se pudo leer metadata.yaml: {e}")

    return duracion_s, n_odom

def leer_pgm(pgm_path):
    with open(pgm_path, 'rb') as f:
        header = []
        while len(header) < 4:
            line = f.readline().decode('ascii', errors='ignore').strip()
            if line.startswith('#'):
                continue
            header.extend(line.split())
        magic  = header[0]
        width  = int(header[1])
        height = int(header[2])

        if magic == 'P5':
            data = np.frombuffer(f.read(), dtype=np.uint8)
        elif magic == 'P2':
            data = np.array(f.read().split(), dtype=np.uint8)
        else:
            raise ValueError(f"Formato PGM no soportado: {magic}")

    return data.reshape((height, width))

def leer_yaml_mapa(yaml_path):
    meta = {'resolution': 0.05, 'origin': [0.0, 0.0, 0.0]}
    if not os.path.exists(yaml_path):
        return meta
    with open(yaml_path) as f:
        for line in f:
            if 'resolution' in line:
                meta['resolution'] = float(line.split(':')[1].strip())
            elif 'origin' in line:
                vals = line.split('[')[1].split(']')[0].split(',')
                meta['origin'] = [float(v) for v in vals]
    return meta

def calcular_cobertura(img):

    libre       = int(np.sum(img >= 230))
    desconocido = int(np.sum((img > 50) & (img < 230)))
    ocupado     = int(np.sum(img <= 50))
    total_acc   = libre + desconocido
    cobertura   = (libre / total_acc * 100.0) if total_acc > 0 else 0.0
    return {
        'libre':        libre,
        'desconocido':  desconocido,
        'ocupado':      ocupado,
        'cobertura_%':  round(cobertura, 1),
    }

def calcular_area_fisica(cob, resolution):
    area_libre = cob['libre']       * resolution**2
    area_desc  = cob['desconocido'] * resolution**2
    area_ocup  = cob['ocupado']     * resolution**2
    return area_libre, area_desc, area_ocup

def plot_trayectoria(img, meta, xs, ys, path_out):
    res    = meta['resolution']
    ox, oy = meta['origin'][0], meta['origin'][1]
    h, w   = img.shape

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(img, cmap='gray', vmin=0, vmax=255,
              extent=[ox, ox + w*res, oy, oy + h*res], origin='lower')

    if xs is not None and ys is not None:
        ax.plot(xs, ys, color='red', lw=1.5, label='Trayectoria /odom')
        ax.scatter(xs[0],  ys[0],  color='lime',   s=80, zorder=5, label='Inicio')
        ax.scatter(xs[-1], ys[-1], color='yellow', s=80, zorder=5,
                   marker='*', label='Fin')
        ax.legend(fontsize=8)
    x0 = ox + 0.1 * w * res
    y0 = oy + 0.05 * h * res
    ax.plot([x0, x0 + 1.0], [y0, y0], 'w-', lw=3)
    ax.text(x0 + 0.5, y0 + 0.05, '1 m', ha='center', color='white', fontsize=8)

    ax.set_xlabel('x (m)')
    ax.set_ylabel('y (m)')
    ax.set_title('Mapa de ocupación + trayectoria odométrica')
    fig.tight_layout()
    fig.savefig(path_out, bbox_inches='tight')
    plt.close(fig)
    print(f'  ✓ {path_out}')

def plot_mapa_cobertura(img, cob, path_out):
    colored = np.zeros((*img.shape, 3), dtype=np.uint8)
    colored[img >= 230]               = [240, 240, 240]
    colored[(img > 50) & (img < 230)] = [128, 128, 128]
    colored[img <= 50]                = [0,   0,   0]

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.imshow(colored, origin='upper')
    libre_p = mpatches.Patch(color=(240/255,)*3,
                             label=f'Libre ({cob["cobertura_%"]:.1f}%)')
    desc_p  = mpatches.Patch(color=(0.5, 0.5, 0.5), label='Desconocido')
    ocup_p  = mpatches.Patch(color='black',          label='Ocupado')
    ax.legend(handles=[libre_p, desc_p, ocup_p], loc='upper right', fontsize=8)
    ax.set_title(f'Mapa de ocupación — cobertura {cob["cobertura_%"]:.1f}%')
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(path_out, bbox_inches='tight')
    plt.close(fig)
    print(f'  ✓ {path_out}')

def generar_latex(modo, distancia, duracion, cob, nodos, cierre_lazo,
                  resolution, area_libre, cierre_arg=None, alineacion='---'):
    label   = 'slam_sim_indicadores' if modo == 'sim' else 'slam_real_indicadores'
    caption = ('Indicadores del mapeo en simulación.'
               if modo == 'sim' else 'Indicadores del mapeo en hardware real.')

    dist_str = f"{distancia:.2f}" if distancia is not None else "---"
    dur_str  = f"{duracion/60:.1f}" if duracion is not None else "---"
    nod_str  = str(nodos) if nodos is not None else "---"
    if cierre_lazo:
        cl_str = 'Sí'
    elif cierre_arg:
        cl_str = 'No detectado'
    else:
        cl_str = 'No determinado'

    lines = [
        f"% Generado por analizar_slam.py — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        r"\begin{table}[H]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{tab:{label}}}",
        r"\begin{tabular}{ll}",
        r"\hline",
        r"\textbf{Indicador} & \textbf{Valor} \\",
        r"\hline",
        f"Tiempo total de mapeo                  & {dur_str}~min \\\\",
        f"Distancia recorrida (odometría)        & {dist_str}~m \\\\",
        f"Número de nodos del grafo de SLAM      & {nod_str} \\\\",
        f"Resolución del mapa                    & {resolution:.2f}~m/celda \\\\",
        f"Cobertura estimada                     & {cob['cobertura_%']:.1f}~\\% \\\\",
        f"Área libre mapeada                     & {area_libre:.2f}~m\\textsuperscript{{2}} \\\\",
        f"Cierre de lazo detectado               & {cl_str} \\\\",
        f"Alineaci\\'on de paredes (inspecci\\'on visual) & {alineacion} \\\\",
        r"\hline",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)

def guardar_csv(modo, distancia, duracion, cob, nodos, resolution,
                area_libre, path_out):
    with open(path_out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['indicador', 'valor', 'unidad'])
        w.writerow(['modo',          modo,                                  ''])
        w.writerow(['distancia_odom', f'{distancia:.3f}' if distancia is not None else '---', 'm'])
        w.writerow(['duracion',       f'{duracion/60:.2f}' if duracion is not None else '---', 'min'])
        w.writerow(['cobertura',      cob['cobertura_%'],                   '%'])
        w.writerow(['celdas_libres',  cob['libre'],                         'celdas'])
        w.writerow(['celdas_desconocidas', cob['desconocido'],              'celdas'])
        w.writerow(['celdas_ocupadas', cob['ocupado'],                      'celdas'])
        w.writerow(['area_libre',     f'{area_libre:.3f}' if area_libre else '---', 'm2'])
        w.writerow(['resolucion',     resolution,                           'm/celda'])
        w.writerow(['nodos_slam',     nodos if nodos is not None else '---', ''])
    print(f'  ✓ {path_out}')

def main():
    parser = argparse.ArgumentParser(
        description='Analiza métricas SLAM. Con --modo solo, descubre rutas automáticamente.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Ejemplo: python3 analizar_slam.py --modo sim --bag <rosbag> --pgm <mapa.pgm>'
    )
    parser.add_argument('--bag',      help='Ruta al rosbag2 (carpeta). Si se omite, se busca el más reciente.', default=None)
    parser.add_argument('--pgm',      help='Ruta al .pgm. Si se omite, se busca el más reciente.', default=None)
    parser.add_argument('--yaml',     help='Ruta al .yaml del mapa (auto si se omite).', default=None)
    parser.add_argument('--modo',     help='sim o real', default=None, choices=['sim', 'real'])
    parser.add_argument('--nodos',    help='Número de nodos SLAM (ingreso manual).', type=int, default=None)
    parser.add_argument('--duracion', help='Duración del mapeo en segundos (si no hay bag).', type=float, default=None)
    parser.add_argument('--alineacion',
                    help='Observación cualitativa sobre alineación de paredes.',
                    default=None)
    parser.add_argument('--cierre',   help='Cierre de lazo detectado: s/n', default=None)
    parser.add_argument('--out',      help='Directorio de salida (auto si se omite).', default=None)
    parser.add_argument('--suffix',   help='Sufijo para los archivos de salida (auto si se omite).', default=None)
    args = parser.parse_args()
    if args.pgm is None and args.bag is None and args.modo is None:
        print("\n=== analizar_slam.py — Modo interactivo ===\n")
        modo_input = input("Modo [sim/real]: ").strip().lower()
        args.modo  = modo_input if modo_input in ('sim', 'real') else 'sim'
        bag_auto, pgm_auto, out_auto = autodescubrir(args.modo)
        mostrar_descubrimiento(args.modo, bag_auto, pgm_auto, out_auto)

        usar_auto = input("¿Usar las rutas anteriores? [S/n]: ").strip().lower()
        if usar_auto not in ('n', 'no'):
            args.bag = bag_auto
            args.pgm = pgm_auto
            if args.out is None:
                args.out = out_auto
        else:
            args.pgm  = input("Ruta al .pgm  (Enter para omitir): ").strip() or None
            args.bag  = input("Ruta al bag   (Enter para omitir): ").strip() or None
            args.yaml = input("Ruta al .yaml (Enter para auto):   ").strip() or None

        d_str = input("Duración del mapeo en segundos (Enter para calcular desde bag): ").strip()
        args.duracion = float(d_str) if d_str else None
        n_str = input("Número de nodos SLAM (Enter para dejar ---): ").strip()
        args.nodos = int(n_str) if n_str else None
        c_str = input("¿Cierre de lazo detectado? [s/n]: ").strip().lower()
        args.cierre = c_str
    elif args.modo is not None and args.bag is None and args.pgm is None:
        bag_auto, pgm_auto, out_auto = autodescubrir(args.modo)
        mostrar_descubrimiento(args.modo, bag_auto, pgm_auto, out_auto)

        if bag_auto is None and pgm_auto is None:
            print("ERROR: No se encontraron archivos automáticamente.")
            print("       Usa --bag y --pgm para especificar las rutas manualmente.")
            sys.exit(1)

        args.bag = args.bag or bag_auto
        args.pgm = args.pgm or pgm_auto
        if args.out is None:
            args.out = out_auto
    modo    = args.modo or 'sim'
    outdir  = args.out  or '.'
    os.makedirs(outdir, exist_ok=True)
    # Sin versionamiento: el sufijo queda fijo por modo, salvo que el usuario indique uno.
    if args.suffix:
        suffix = args.suffix
    else:
        suffix = modo

    cierre_lazo = (args.cierre or '').lower().startswith('s')

    alineacion_str = args.alineacion or '---'

    print(f"\n{'═'*60}")
    print(f"  Analizando SLAM — modo: {modo}")
    print(f"  Suffix de salida: {suffix}")
    print(f"  Directorio de salida: {outdir}")
    print(f"{'═'*60}")
    t_arr = x_arr = y_arr = None
    distancia = None
    duracion  = args.duracion

    if args.bag:
        if not os.path.isdir(args.bag):
            print(f"\n  AVISO: Carpeta de bag no encontrada: {args.bag}")
        else:
            print(f"\n[1] Leyendo rosbag: {args.bag}")
            t_arr, x_arr, y_arr = leer_odom_bag(args.bag)
            if x_arr is not None:
                distancia = calcular_distancia(x_arr, y_arr)
                if duracion is None and t_arr is not None:
                    duracion = float(t_arr[-1] - t_arr[0])
                print(f"    Mensajes /odom : {len(x_arr)}")
                print(f"    Distancia      : {distancia:.3f} m")
                print(f"    Duración       : {duracion/60:.2f} min")
            else:
                print("    rosbag2_py no disponible — intentando con rosbags...")
                t_arr, x_arr, y_arr = leer_odom_bag_rosbags(args.bag)
                if x_arr is not None:
                    distancia = calcular_distancia(x_arr, y_arr)
                    if duracion is None and t_arr is not None:
                        duracion = float(t_arr[-1] - t_arr[0])
                    print(f"    Distancia (rosbags)   : {distancia:.3f} m")
                    print(f"    Duración  (rosbags)   : {duracion/60:.2f} min")
                else:
                    print("    rosbags no disponible — leyendo bag con sqlite3...")
                    t_arr, x_arr, y_arr = leer_odom_bag_sqlite(args.bag)
                    if x_arr is not None:
                        distancia = calcular_distancia(x_arr, y_arr)
                        if duracion is None and t_arr is not None:
                            duracion = float(t_arr[-1] - t_arr[0])
                        print(f"    Distancia (sqlite3)   : {distancia:.3f} m")
                        print(f"    Duración  (sqlite3)   : {duracion/60:.2f} min")
                    else:
                        print("    Leyendo metadata.yaml para duración...")
                        dur_meta, _ = leer_metadata_bag(args.bag)
                        if dur_meta is not None and duracion is None:
                            duracion = dur_meta
                            print(f"    Duración (metadata.yaml): {duracion/60:.2f} min")
                        print("    Distancia: no disponible")
    else:
        print("\n[1] Sin bag — distancia y duración quedarán como '---'")
    resolution = 0.05
    cob  = {'libre': 0, 'desconocido': 0, 'ocupado': 0, 'cobertura_%': 0.0}
    img  = None
    meta = {'resolution': 0.05, 'origin': [0.0, 0.0, 0.0]}
    area_libre = 0.0

    if args.pgm:
        if not os.path.exists(args.pgm):
            print(f"\n  AVISO: PGM no encontrado: {args.pgm}")
        else:
            print(f"\n[2] Analizando mapa: {args.pgm}")
            img        = leer_pgm(args.pgm)
            yaml_path  = args.yaml or args.pgm.replace('.pgm', '.yaml')
            meta       = leer_yaml_mapa(yaml_path)
            resolution = meta['resolution']
            cob        = calcular_cobertura(img)
            area_libre, _, _ = calcular_area_fisica(cob, resolution)
            print(f"    Dimensiones : {img.shape[1]}×{img.shape[0]} celdas")
            print(f"    Resolución  : {resolution} m/celda")
            print(f"    Cobertura   : {cob['cobertura_%']:.1f}%")
            print(f"    Área libre  : {area_libre:.2f} m²")
    else:
        print("\n[2] Sin PGM — métricas de cobertura quedarán en 0")
    print("\n[3] Generando gráficos...")
    if img is not None:
        plot_trayectoria(img, meta, x_arr, y_arr,
                         os.path.join(outdir, f'slam_trayectoria_{suffix}.png'))
        plot_mapa_cobertura(img, cob,
                            os.path.join(outdir, f'slam_mapa_vis_{suffix}.png'))
    else:
        print("  Sin PGM — gráficos omitidos.")
    print("[4] Generando tablas...")
    guardar_csv(modo, distancia, duracion, cob, args.nodos,
                resolution, area_libre,
                os.path.join(outdir, f'slam_metricas_{suffix}.csv'))

    latex    = generar_latex(modo, distancia, duracion, cob, args.nodos,
                             cierre_lazo, resolution, area_libre,
                             cierre_arg=args.cierre,
                            alineacion=alineacion_str)
    tex_path = os.path.join(outdir, f'slam_tabla_{suffix}.tex')
    with open(tex_path, 'w') as f:
        f.write(latex)
    print(f'  ✓ {tex_path}')
    print(f"\n{'═'*60}")
    print("  RESUMEN PARA LA TESIS")
    print(f"{'═'*60}")
    print(f"  Imágenes generadas en:  {outdir}/")
    print(f"    slam_trayectoria_{suffix}.png")
    print(f"    slam_mapa_vis_{suffix}.png")
    print(f"  Tabla LaTeX:  slam_tabla_{suffix}.tex")
    print(f"  CSV:          slam_metricas_{suffix}.csv")
    print(f"{'═'*60}\n")

if __name__ == '__main__':
    main()