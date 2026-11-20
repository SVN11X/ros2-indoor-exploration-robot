#!/usr/bin/env python3
"""Dibuja el plano del recinto de ensayo (Fig. A8.1 de la tesis).

Uso:
    python3 dibujar_plano_recinto.py [--salida carpeta]

Toma las distancias de comparar_mapa_plano.py, de modo que el plano de la
figura y el de la comparación con los mapas son el mismo. Las medidas son
distancias libres entre muros, tomadas a mano en el recinto. Los muros tienen
menos de 2 cm de espesor y se dibujan como líneas. El largo del tabique corto
inferior no se midió, por lo que se dibuja con su largo aproximado y sin cota.

Genera plano_recinto.pdf y plano_recinto.png.
Requiere numpy, scipy, pillow y matplotlib.
"""
import argparse, os, sys
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comparar_mapa_plano as cp

MURO = '#333333'
COTA = '#1f5fa8'


def cota(ax, p0, p1, valor, rot=0):
    """Flecha de cota entre p0 y p1 con la medida al centro."""
    ax.annotate('', xy=p1, xytext=p0,
                arrowprops=dict(arrowstyle='<|-|>', color=COTA, lw=1.0, mutation_scale=9, shrinkA=0, shrinkB=0))
    mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
    ax.text(mx, my, f'{valor:.2f} m', color=COTA, fontsize=14, rotation=rot, ha='center', va='center',
            bbox=dict(boxstyle='square,pad=0.12', fc='white', ec='none'))


def dibujar(ax):
    W, H, X1, X2 = cp.W, cp.H, cp.X1, cp.X2
    for a, b in cp.PLANO.values():
        ax.plot([a[0], b[0]], [a[1], b[1]], '-', color=MURO, lw=4, solid_capstyle='butt', zorder=3)
    # alto del recinto y ancho del tercer pasillo
    cota(ax, (-0.16, 0), (-0.16, H), cp.ALTO, rot=90)
    cota(ax, (X2, H + 0.13), (W, H + 0.13), cp.PASILLO_3)
    # primer y segundo pasillo
    cota(ax, (0, 0.35), (X1, 0.35), cp.PASILLO_1)
    cota(ax, (X1, 0.95), (X2, 0.95), cp.PASILLO_2)
    # pasos que dejan los muros largos
    cota(ax, (X1 - 0.08, H - cp.PASO_1), (X1 - 0.08, H), cp.PASO_1, rot=90)
    cota(ax, (X2 - 0.08, 0), (X2 - 0.08, cp.PASO_2), cp.PASO_2, rot=90)
    # tabique superior derecho
    cota(ax, (W - 0.27, H - cp.TAB_SUP_DIST), (W - 0.27, H), cp.TAB_SUP_DIST, rot=90)
    cota(ax, (W - cp.TAB_SUP_LARGO, H - cp.TAB_SUP_DIST - 0.08), (W, H - cp.TAB_SUP_DIST - 0.08), cp.TAB_SUP_LARGO)
    # tabique unido al segundo muro largo
    y_tm = cp.PASO_2 + cp.TAB_MEDIO_ALTURA
    cota(ax, (X2, y_tm + 0.08), (X2 + cp.TAB_MEDIO_LARGO, y_tm + 0.08), cp.TAB_MEDIO_LARGO)
    cota(ax, (X2 + 0.10, cp.PASO_2), (X2 + 0.10, y_tm), cp.TAB_MEDIO_ALTURA, rot=90)
    # tabique corto unido al muro inferior
    cota(ax, (W - cp.TAB_INF_DIST, 0.12), (W, 0.12), cp.TAB_INF_DIST)
    ax.set_aspect('equal')
    ax.set_xlim(-0.30, W + 0.15)
    ax.set_ylim(-0.12, H + 0.25)
    ax.axis('off')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--salida', default='.')
    a = ap.parse_args(); os.makedirs(a.salida, exist_ok=True)
    disponibles = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams['font.family'] = [f for f in ('Arial', 'Liberation Sans', 'DejaVu Sans') if f in disponibles][:1] or ['sans-serif']
    fig, ax = plt.subplots(figsize=(7.4, 7.0))
    dibujar(ax)
    fig.tight_layout()
    fig.savefig(os.path.join(a.salida, 'plano_recinto.pdf'))
    fig.savefig(os.path.join(a.salida, 'plano_recinto.png'), dpi=200)
    plt.close(fig)
    print('Figura:', os.path.join(a.salida, 'plano_recinto.pdf'))


if __name__ == '__main__':
    main()
