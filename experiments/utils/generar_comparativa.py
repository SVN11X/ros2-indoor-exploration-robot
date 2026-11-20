#!/usr/bin/env python3
import argparse
import csv
import glob
import os
import sys
from datetime import datetime

try:
    import numpy as np
except ImportError:
    print("ERROR: numpy no disponible. Instalar con: pip install numpy")
    sys.exit(1)

try:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    HAS_MPL = False

def leer_csv_metricas(csv_path):

    if not os.path.isfile(csv_path):
        return {}
    out = {}
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    out[row[0].strip()] = row[1].strip()
    except Exception as e:
        print(f"  AVISO leyendo {csv_path}: {e}")
    return out

def parsear_valor_numerico(s):

    if s is None or s == '' or s == '---':
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None

def recolectar_iteraciones(sesion_dir):

    pattern = os.path.join(sesion_dir, 'iteracion_*')
    iter_dirs = sorted(glob.glob(pattern))

    iteraciones = []
    for iter_dir in iter_dirs:
        nombre = os.path.basename(iter_dir)
        partes = nombre.split('_')
        try:
            num = int(partes[1])
        except (IndexError, ValueError):
            print(f"  AVISO: nombre de iteración no parseable: {nombre}")
            continue

        explore_csv = glob.glob(os.path.join(iter_dir, 'exploracion', 'explore_metricas_*.csv'))
        slam_csv    = glob.glob(os.path.join(iter_dir, 'mapeo',       'slam_metricas_*.csv'))

        m_exp  = leer_csv_metricas(explore_csv[0]) if explore_csv else {}
        m_slam = leer_csv_metricas(slam_csv[0])    if slam_csv    else {}

        merged = {
            'iteracion':           num,
            'nombre':              nombre,
            'duracion_min':        parsear_valor_numerico(m_exp.get('duracion')),
            'metas_generadas':     parsear_valor_numerico(m_exp.get('metas_generadas')),
            'metas_alcanzadas':    parsear_valor_numerico(m_exp.get('metas_alcanzadas')),
            'metas_fallidas':      parsear_valor_numerico(m_exp.get('metas_fallidas')),
            'tasa_exito_pct':      parsear_valor_numerico(m_exp.get('tasa_exito')),
            'cobertura_pct':       parsear_valor_numerico(m_exp.get('cobertura')),
            'area_libre_m2':       parsear_valor_numerico(m_exp.get('area_libre')),
            'distancia_total_m':   parsear_valor_numerico(m_exp.get('distancia_total')),
            'intervenciones':      parsear_valor_numerico(m_exp.get('intervenciones')),

            'distancia_slam_m':    parsear_valor_numerico(m_slam.get('distancia_recorrida_m')),
            'duracion_slam_min':   parsear_valor_numerico(m_slam.get('duracion_min')),
            'cobertura_slam_pct':  parsear_valor_numerico(m_slam.get('cobertura_pct')),
            'nodos_slam':          parsear_valor_numerico(m_slam.get('nodos_slam')),
        }
        iteraciones.append(merged)

    iteraciones.sort(key=lambda x: x['iteracion'])
    return iteraciones

def calcular_estadisticas(iteraciones, campo):

    valores = [it[campo] for it in iteraciones if it.get(campo) is not None]
    if not valores:
        return None, None, 0
    arr = np.array(valores, dtype=float)
    return float(arr.mean()), float(arr.std(ddof=1)) if len(arr) > 1 else 0.0, len(arr)

def fmt(valor, decimales=2, dash='---'):

    if valor is None:
        return dash
    if isinstance(valor, float) and (np.isnan(valor) or np.isinf(valor)):
        return dash
    return f"{valor:.{decimales}f}"

def generar_csv_comparativa(iteraciones, csv_path):

    if not iteraciones:
        return

    campos = [
        ('iteracion',          'Iter',           0),
        ('duracion_min',       'Duración (min)', 2),
        ('metas_generadas',    'Metas',          0),
        ('metas_alcanzadas',   'Éxitos',         0),
        ('metas_fallidas',     'Fallos',         0),
        ('tasa_exito_pct',     'Tasa éxito (%)', 1),
        ('cobertura_pct',      'Cobertura (%)',  1),
        ('distancia_total_m',  'Distancia (m)',  1),
        ('intervenciones',     'Intervenciones', 0),
        ('nodos_slam',         'Nodos SLAM',     0),
    ]

    headers = [h[1] for h in campos]

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for it in iteraciones:
            row = []
            for campo, _, dec in campos:
                row.append(fmt(it.get(campo), dec))
            writer.writerow(row)

        media_row = ['μ (media)']
        std_row   = ['σ (desv. std)']
        for campo, _, dec in campos[1:]:
            media, std, n = calcular_estadisticas(iteraciones, campo)
            media_row.append(fmt(media, dec))
            std_row.append(fmt(std, dec))
        writer.writerow(media_row)
        writer.writerow(std_row)

    print(f"  ✓ CSV comparativa: {csv_path}")

def generar_latex_comparativa(iteraciones, tex_path, sesion_id=''):

    if not iteraciones:
        return

    n_iter = len(iteraciones)

    col_spec = 'r' + 'r' * 8
    header = (
        r'\textbf{Iter} & '
        r'\textbf{Dur (min)} & '
        r'\textbf{Metas} & '
        r'\textbf{Éxitos} & '
        r'\textbf{Fallos} & '
        r'\textbf{Tasa (\%)} & '
        r'\textbf{Cobert. (\%)} & '
        r'\textbf{Dist (m)} & '
        r'\textbf{Interv.} \\'
    )

    rows = []
    for it in iteraciones:
        row = ' & '.join([
            str(it['iteracion']),
            fmt(it.get('duracion_min'), 1),
            fmt(it.get('metas_generadas'), 0),
            fmt(it.get('metas_alcanzadas'), 0),
            fmt(it.get('metas_fallidas'), 0),
            fmt(it.get('tasa_exito_pct'), 1),
            fmt(it.get('cobertura_pct'), 1),
            fmt(it.get('distancia_total_m'), 2),
            fmt(it.get('intervenciones'), 0),
        ]) + r' \\'
        rows.append(row)

    campos_stat = [
        ('duracion_min',      1),
        ('metas_generadas',   0),
        ('metas_alcanzadas',  0),
        ('metas_fallidas',    0),
        ('tasa_exito_pct',    1),
        ('cobertura_pct',     1),
        ('distancia_total_m', 2),
        ('intervenciones',    0),
    ]
    media_vals = []
    std_vals = []
    for campo, dec in campos_stat:
        m, s, _ = calcular_estadisticas(iteraciones, campo)
        media_vals.append(fmt(m, dec))
        std_vals.append(fmt(s, dec))

    media_row = r'$\mu$ & ' + ' & '.join(media_vals) + r' \\'
    std_row   = r'$\sigma$ & ' + ' & '.join(std_vals) + r' \\'

    lines = [
        f'% Tabla comparativa generada por generar_comparativa.py',
        f'% Sesión: {sesion_id}',
        f'% Fecha:  {datetime.now().strftime("%Y-%m-%d %H:%M")}',
        f'% Iteraciones: {n_iter}',
        '',
        r'\begin{table}[H]',
        r'\centering',
        r'\caption{Comparativa de iteraciones de exploración autónoma. '
        r'Cada iteración corresponde a una ejecución independiente desde '
        r'cero (reset completo de SLAM y Nav2 entre iteraciones).}',
        r'\label{tab:comparativa_iteraciones}',
        r'\resizebox{\textwidth}{!}{%',
        r'\begin{tabular}{' + col_spec + r'}',
        r'\hline',
        header,
        r'\hline',
    ]
    lines.extend(rows)
    lines.extend([
        r'\hline',
        media_row,
        std_row,
        r'\hline',
        r'\end{tabular}',
        r'}',
        r'\end{table}',
    ])

    with open(tex_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(f"  ✓ LaTeX comparativa: {tex_path}")

def generar_grafico_barras(iteraciones, png_path):

    if not HAS_MPL:
        print("  AVISO: matplotlib no disponible, omitiendo gráfico")
        return
    if not iteraciones:
        return

    iters = [it['iteracion'] for it in iteraciones]
    metas  = [it.get('metas_generadas',  0) or 0 for it in iteraciones]
    exitos = [it.get('metas_alcanzadas', 0) or 0 for it in iteraciones]
    fallos = [it.get('metas_fallidas',   0) or 0 for it in iteraciones]
    cobert = [it.get('cobertura_pct',    0) or 0 for it in iteraciones]
    distancia = [it.get('distancia_total_m', 0) or 0 for it in iteraciones]

    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    ax = axes[0, 0]
    x = np.arange(len(iters))
    w = 0.25
    ax.bar(x - w, metas,  w, label='Generadas')
    ax.bar(x,     exitos, w, label='Alcanzadas')
    ax.bar(x + w, fallos, w, label='Fallidas')
    ax.set_xticks(x)
    ax.set_xticklabels([f'Iter {i}' for i in iters])
    ax.set_ylabel('Cantidad')
    ax.set_title('Metas por iteración')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)

    ax = axes[0, 1]
    ax.bar(x, cobert)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Iter {i}' for i in iters])
    ax.set_ylabel('Cobertura (%)')
    ax.set_title('Cobertura del entorno')
    ax.set_ylim([0, 100])
    ax.grid(axis='y', alpha=0.3)
    for i, v in enumerate(cobert):
        ax.text(i, v + 1, f'{v:.1f}%', ha='center', fontsize=9)

    ax = axes[1, 0]
    ax.bar(x, distancia)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Iter {i}' for i in iters])
    ax.set_ylabel('Distancia (m)')
    ax.set_title('Distancia recorrida')
    ax.grid(axis='y', alpha=0.3)

    tasa = [it.get('tasa_exito_pct', 0) or 0 for it in iteraciones]
    ax = axes[1, 1]
    ax.bar(x, tasa)
    ax.set_xticks(x)
    ax.set_xticklabels([f'Iter {i}' for i in iters])
    ax.set_ylabel('Tasa de éxito (%)')
    ax.set_title('Tasa de éxito de metas')
    ax.set_ylim([0, 105])
    ax.grid(axis='y', alpha=0.3)
    for i, v in enumerate(tasa):
        ax.text(i, v + 2, f'{v:.0f}%', ha='center', fontsize=9)

    plt.tight_layout()
    plt.savefig(png_path, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"  ✓ Gráfico: {png_path}")

def main():
    parser = argparse.ArgumentParser(
        description='Genera comparativa de iteraciones de una sesión de mapeo.')
    parser.add_argument('--sesion-dir', required=True,
                        help='Carpeta de sesión (con subcarpetas iteracion_NN_*)')
    parser.add_argument('--output', default=None,
                        help='Directorio de salida (default: --sesion-dir)')
    args = parser.parse_args()

    if not os.path.isdir(args.sesion_dir):
        print(f"ERROR: No es un directorio: {args.sesion_dir}")
        sys.exit(1)

    output_dir = args.output or args.sesion_dir
    os.makedirs(output_dir, exist_ok=True)

    print(f"\n{'═'*60}")
    print(f"  Generando comparativa de sesión")
    print(f"  Sesión: {args.sesion_dir}")
    print(f"  Salida: {output_dir}")
    print(f"{'═'*60}\n")

    iteraciones = recolectar_iteraciones(args.sesion_dir)

    if not iteraciones:
        print("  AVISO: No se encontraron iteraciones en la sesión")
        sys.exit(0)

    print(f"  Iteraciones encontradas: {len(iteraciones)}")
    for it in iteraciones:
        print(f"    - {it['nombre']}")
    print()

    csv_path = os.path.join(output_dir, 'comparativa_iteraciones.csv')
    tex_path = os.path.join(output_dir, 'comparativa_iteraciones.tex')
    png_path = os.path.join(output_dir, 'comparativa_metricas.png')

    sesion_id = os.path.basename(args.sesion_dir)

    generar_csv_comparativa(iteraciones, csv_path)
    generar_latex_comparativa(iteraciones, tex_path, sesion_id)
    generar_grafico_barras(iteraciones, png_path)

    print(f"\n{'═'*60}")
    print(f"  ✓ Comparativa generada exitosamente")
    print(f"{'═'*60}\n")

if __name__ == '__main__':
    main()