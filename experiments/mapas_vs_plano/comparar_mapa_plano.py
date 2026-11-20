#!/usr/bin/env python3
"""Compara los mapas de ocupación del robot con el plano medido del recinto.

Uso:
    python3 comparar_mapa_plano.py mapa1 mapa2 ... [--salida carpeta]

Cada mapa puede ser:
  * el archivo PGM del mapa (mapa_explore_real.pgm), o
  * la imagen de cobertura que genera analizar_slam.py (PNG), de la que se
    recupera la clasificación de cada celda (libre, ocupada o desconocida).

Pasos:
  1. Obtiene la rejilla del mapa con resolución de 0.05 m/celda.
  2. Alinea el plano con cada mapa mediante una rotación y una traslación
     (transformación rígida) que minimiza la distancia entre las celdas
     ocupadas y los muros del plano, con un tope de 0.15 m por celda para que
     los objetos fuera del plano no desplacen el ajuste.
  3. Calcula la distancia de cada punto del plano a la celda ocupada más
     cercana (métrica de Santos et al. 2013, aplicada por Trejos et al. 2022),
     solo en los tramos que el robot observó.
  4. Mide en el mapa las mismas distancias del plano y las compara.

El largo del tabique corto inferior no se midió. Se dibuja con un largo
aproximado y sin cota, y la tabla de distancias solo usa su posición. La
Fig. A8.1 se dibuja con dibujar_plano_recinto.py, que usa las mismas
distancias de este archivo.
Requiere numpy, scipy, pillow y matplotlib.
"""
import argparse, os, re
import numpy as np
from PIL import Image
from scipy import ndimage, optimize
from scipy.spatial import cKDTree

RES = 0.05  # m/celda

# ----------------------------------------------------------------- plano
# Distancias libres entre muros medidas a mano en el recinto (m), Fig. A8.1.
# Si el recinto se vuelve a medir, basta con cambiar estos valores.
ALTO = 1.91              # alto interior del recinto
PASILLO_1 = 0.58         # ancho del primer pasillo
PASILLO_2 = 0.58         # ancho del segundo pasillo
PASILLO_3 = 0.98         # ancho del tercer pasillo
PASO_1 = 0.68            # paso entre el extremo del primer muro largo y el muro superior
PASO_2 = 0.68            # paso entre el extremo del segundo muro largo y el muro inferior
TAB_MEDIO_LARGO = 0.40   # largo del tabique unido al segundo muro largo
TAB_MEDIO_ALTURA = 0.40  # altura de ese tabique sobre el extremo del muro
TAB_SUP_DIST = 0.40      # distancia del tabique superior derecho al muro superior
TAB_SUP_LARGO = 0.40     # largo del tabique superior derecho
TAB_INF_DIST = 0.61      # distancia del tabique corto inferior al muro derecho
TAB_INF_LARGO = 0.30     # largo aproximado del tabique corto inferior (no medido)

# Origen en la esquina interior inferior izquierda, muros delgados.
W, H = PASILLO_1 + PASILLO_2 + PASILLO_3, ALTO
X1, X2 = PASILLO_1, PASILLO_1 + PASILLO_2          # posición de los muros largos
PLANO = {
    'muro_inferior':  ((0, 0), (W, 0)),
    'muro_derecho':   ((W, 0), (W, H)),
    'muro_superior':  ((0, H), (W, H)),
    'muro_izquierdo': ((0, 0), (0, H)),
    'muro_largo_1':   ((X1, 0), (X1, H - PASO_1)),
    'muro_largo_2':   ((X2, PASO_2), (X2, H)),
    'tabique_sup_der':((W - TAB_SUP_LARGO, H - TAB_SUP_DIST), (W, H - TAB_SUP_DIST)),
    'tabique_medio':  ((X2, PASO_2 + TAB_MEDIO_ALTURA), (X2 + TAB_MEDIO_LARGO, PASO_2 + TAB_MEDIO_ALTURA)),
    'tabique_inf':    ((W - TAB_INF_DIST, 0), (W - TAB_INF_DIST, TAB_INF_LARGO)),
}

def muestrear(segs, paso):
    pts, lab = [], []
    for k, (a, b) in segs.items():
        a, b = np.array(a, float), np.array(b, float)
        n = max(2, int(np.ceil(np.linalg.norm(b - a) / paso)) + 1)
        t = np.linspace(0, 1, n)
        pts.append(a + (b - a) * t[:, None]); lab += [k] * n
    return np.vstack(pts), np.array(lab)

# Transformada de distancia de los muros del plano, para evaluar el ajuste rápido
_FR, _MG = 0.005, 0.6
_nx, _ny = int((W + 2 * _MG) / _FR) + 1, int((H + 2 * _MG) / _FR) + 1
_mask = np.ones((_ny, _nx), bool)
_P, _ = muestrear(PLANO, 0.002)
_mask[np.round((_P[:, 1] + _MG) / _FR).astype(int), np.round((_P[:, 0] + _MG) / _FR).astype(int)] = False
_DT = ndimage.distance_transform_edt(_mask) * _FR

def dist_muros(p):
    ix, iy = (p[:, 0] + _MG) / _FR, (p[:, 1] + _MG) / _FR
    out = np.full(len(p), _MG)
    ok = (ix >= 0) & (ix < _nx - 1) & (iy >= 0) & (iy < _ny - 1)
    out[ok] = ndimage.map_coordinates(_DT, [iy[ok], ix[ok]], order=1)
    return out

# ----------------------------------------------------------------- mapas
def leer_pgm(path):
    with open(path, 'rb') as f:
        head = []
        while len(head) < 4:
            line = f.readline().decode('ascii', 'ignore').strip()
            if not line.startswith('#'):
                head += line.split()
        w, h = int(head[1]), int(head[2])
        data = np.frombuffer(f.read(), np.uint8) if head[0] == 'P5' else np.array(f.read().split(), np.uint8)
    img = data.reshape(h, w)
    g = np.full(img.shape, 1)          # 0 libre, 1 desconocido, 2 ocupado (umbrales de la Ec. A8.1)
    g[img >= 230] = 0
    g[img <= 50] = 2
    return g

def leer_imagen_cobertura(path):
    """Recupera la rejilla desde la imagen de analizar_slam.py.
    Colores: libre 240, desconocido 128, ocupado 0 (y sus versiones bajo la leyenda)."""
    gris = np.array(Image.open(path).convert('RGB')).astype(int)[:, :, 0]
    clase = np.full(gris.shape, -1)
    clase[np.isin(gris, (240, 251, 252))] = 0
    clase[np.isin(gris, (128, 229, 230))] = 1
    clase[np.isin(gris, (0, 203, 204))] = 2
    fondo = gris != 255
    filas = np.where(fondo.mean(axis=1) > 0.5)[0]
    cols = np.where(fondo.mean(axis=0) > 0.5)[0]
    sub = clase[filas.min():filas.max() + 1, cols.min():cols.max() + 1]
    def bordes(eje):
        pos = []
        for i in range(0, sub.shape[1 - eje], 3):
            v = sub[:, i] if eje == 0 else sub[i, :]
            idx = np.where((v[1:] != v[:-1]) & (v[1:] >= 0) & (v[:-1] >= 0))[0] + 1
            pos += idx.tolist()
        return np.array(pos, float)
    def n_celdas(pos, largo):
        punt = []
        for n in range(15, 121):
            s = largo / n; r = pos % s
            punt.append((n, np.mean(np.minimum(r, s - r) < 0.75)))
        mejor = max(p for _, p in punt)
        return min(n for n, p in punt if p >= 0.95 * mejor)
    ncol = n_celdas(bordes(1), sub.shape[1]); nfil = n_celdas(bordes(0), sub.shape[0])
    sx, sy = sub.shape[1] / ncol, sub.shape[0] / nfil
    g = np.full((nfil, ncol), 1)
    for i in range(nfil):
        for j in range(ncol):
            blk = sub[int(round(i * sy + 0.2 * sy)):int(round((i + 1) * sy - 0.2 * sy)),
                      int(round(j * sx + 0.2 * sx)):int(round((j + 1) * sx - 0.2 * sx))].ravel()
            blk = blk[blk >= 0]
            if blk.size:
                v, c = np.unique(blk, return_counts=True); g[i, j] = v[np.argmax(c)]
    return g

def leer_mapa(path):
    return leer_pgm(path) if path.lower().endswith('.pgm') else leer_imagen_cobertura(path)

def celdas(g, clase):
    r, c = np.where(g == clase)
    return np.c_[c * RES, -r * RES]

def transformar(p, th, tx, ty):
    c, s = np.cos(th), np.sin(th)
    return np.c_[c * p[:, 0] - s * p[:, 1] + tx, s * p[:, 0] + c * p[:, 1] + ty]

# ----------------------------------------------------------------- ajuste
def alinear(g):
    occ = celdas(g, 2); cen = occ.mean(axis=0); q0 = occ - cen
    costo = lambda p: np.mean(np.minimum(dist_muros(transformar(q0, *p)), 0.15) ** 2)
    cand = []
    for thd in np.arange(0, 360, 3):              # búsqueda gruesa de la orientación
        th = np.radians(thd)
        for dx in np.arange(-0.3, 0.31, 0.1):
            for dy in np.arange(-0.3, 0.31, 0.1):
                p = [th, W / 2 + dx, H / 2 + dy]; cand.append((costo(p), p))
    cand.sort(key=lambda c: c[0])
    mejor = None
    for _, p in cand[:20]:                        # ajuste fino desde los mejores candidatos
        r = optimize.minimize(costo, p, method='Nelder-Mead',
                              options=dict(xatol=1e-6, fatol=1e-10, maxiter=6000))
        if mejor is None or r.fun < mejor.fun:
            mejor = r
    return mejor.x, cen

def zona_evaluada(q):
    return (q[:, 0] > -0.15) & (q[:, 0] < W + 0.15) & (q[:, 1] > -0.15) & (q[:, 1] < H + 0.15)

def ajustar_muro(qo, k, radio=0.12):
    a, b = (np.array(v, float) for v in PLANO[k])
    u = (b - a) / np.linalg.norm(b - a); n = np.array([-u[1], u[0]]); L = np.linalg.norm(b - a)
    rel = qo - a; s, d = rel @ u, rel @ n
    sel = (np.abs(d) < radio) & (s > -0.08) & (s < L + 0.08)
    return float(np.median(d[sel])), float(s[sel].min()), float(s[sel].max())

def medir(qo):
    off = {k: ajustar_muro(qo, k) for k in PLANO}
    y_sup = H + off['muro_superior'][0]; y_inf = off['muro_inferior'][0]
    x_izq = -off['muro_izquierdo'][0]; x_der = W - off['muro_derecho'][0]
    x_l1 = X1 - off['muro_largo_1'][0]; x_l2 = X2 - off['muro_largo_2'][0]
    fin_l1 = off['muro_largo_1'][2]; ini_l2 = PASO_2 + off['muro_largo_2'][1]
    y_tm = (PASO_2 + TAB_MEDIO_ALTURA) + off['tabique_medio'][0]; fin_tm = X2 + off['tabique_medio'][2]
    y_tsd = (H - TAB_SUP_DIST) + off['tabique_sup_der'][0]; ini_tsd = (W - TAB_SUP_LARGO) + off['tabique_sup_der'][1]
    x_ti = (W - TAB_INF_DIST) - off['tabique_inf'][0]
    return [
        ('Alto interior del recinto', ALTO, y_sup - y_inf),
        ('Ancho del primer pasillo', PASILLO_1, x_l1 - x_izq),
        ('Ancho del segundo pasillo', PASILLO_2, x_l2 - x_l1),
        ('Ancho del tercer pasillo', PASILLO_3, x_der - x_l2),
        ('Paso sobre el primer muro largo', PASO_1, y_sup - fin_l1),
        ('Paso bajo el segundo muro largo', PASO_2, ini_l2 - y_inf),
        ('Largo del tabique unido al segundo muro largo', TAB_MEDIO_LARGO, fin_tm - x_l2),
        ('Altura de ese tabique sobre el extremo del muro', TAB_MEDIO_ALTURA, y_tm - ini_l2),
        ('Distancia del tabique superior derecho al muro superior', TAB_SUP_DIST, y_sup - y_tsd),
        ('Largo del tabique superior derecho', TAB_SUP_LARGO, x_der - ini_tsd),
        ('Distancia del tabique corto inferior al muro derecho', TAB_INF_DIST, x_der - x_ti),
    ]

def evaluar(g):
    (th, tx, ty), cen = alinear(g)
    qo = transformar(celdas(g, 2) - cen, th, tx, ty)
    qf = transformar(celdas(g, 0) - cen, th, tx, ty)
    P, _ = muestrear(PLANO, 0.01)
    observado = cKDTree(qf).query(P, distance_upper_bound=0.10)[0] < np.inf
    d_plano_mapa = cKDTree(qo).query(P[observado])[0]
    d_mapa_plano = dist_muros(qo[zona_evaluada(qo)])
    return dict(theta=np.degrees(th) % 360, qo=qo, qf=qf, observado=observado.mean(),
                d_pm=d_plano_mapa, d_mp=d_mapa_plano, medidas=medir(qo))

# ----------------------------------------------------------------- salidas
def figura(res, nombres, path):
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    disponibles = {f.name for f in font_manager.fontManager.ttflist}
    plt.rcParams['font.family'] = [f for f in ('Arial', 'Liberation Sans', 'DejaVu Sans') if f in disponibles][:1] or ['sans-serif']
    n = len(res); cols = 3; filas = int(np.ceil((n + 1) / cols))
    fig, axs = plt.subplots(filas, cols, figsize=(5.0 * cols, 4.6 * filas)); axs = axs.ravel()
    for ax, r, nom in zip(axs, res, nombres):
        ax.scatter(r['qf'][:, 0], r['qf'][:, 1], s=13, c='#dcdcdc', marker='s', linewidths=0)
        ax.scatter(r['qo'][:, 0], r['qo'][:, 1], s=13, c='#111111', marker='s', linewidths=0)
        for a, b in PLANO.values():
            ax.plot([a[0], b[0]], [a[1], b[1]], '-', color='#c0392b', lw=2.0)
        ax.set_aspect('equal'); ax.set_xlim(-0.3, W + 0.3); ax.set_ylim(-0.3, H + 0.25)
        ax.set_title(nom, fontsize=13); ax.set_xlabel('x (m)'); ax.set_ylabel('y (m)'); ax.grid(alpha=0.25)
    for ax in axs[n:]:
        ax.axis('off')
    from matplotlib.lines import Line2D
    h = [Line2D([], [], ls='', marker='s', color='#dcdcdc', ms=8), Line2D([], [], ls='', marker='s', color='#111111', ms=8),
         Line2D([], [], color='#c0392b', lw=2)]
    axs[n].legend(h, ['Celda libre del mapa', 'Celda ocupada del mapa', 'Muro del plano'],
                  loc='center', fontsize=12, frameon=False)
    fig.tight_layout(); fig.savefig(path, dpi=150)
    fig.savefig(os.path.splitext(path)[0] + '.pdf'); plt.close(fig)

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mapas', nargs='+'); ap.add_argument('--salida', default='comparacion_plano')
    ap.add_argument('--nombres', nargs='*')
    a = ap.parse_args(); os.makedirs(a.salida, exist_ok=True)
    nombres = a.nombres or [os.path.splitext(os.path.basename(m))[0] for m in a.mapas]
    res = []
    for m, nom in zip(a.mapas, nombres):
        g = leer_mapa(m); r = evaluar(g); res.append(r)
        libre = int((g == 0).sum()); desc = int((g == 1).sum())
        print(f"{nom}: {g.shape[0]}x{g.shape[1]} celdas, área libre {libre * RES**2:.3f} m2, "
              f"cobertura {100 * libre / (libre + desc):.1f}%, rotación {r['theta']:.1f} grados")
        print(f"   plano->mapa: media {100 * r['d_pm'].mean():.2f} cm, p95 {100 * np.percentile(r['d_pm'], 95):.1f} cm "
              f"(tramos observados {100 * r['observado']:.0f}%) | mapa->plano: media {100 * r['d_mp'].mean():.2f} cm, "
              f"p95 {100 * np.percentile(r['d_mp'], 95):.1f} cm")
    print('\nMedida | plano (m) | media mapas (m) | mín | máx | diferencia (cm)')
    for i, (txt, ref, _) in enumerate(res[0]['medidas']):
        v = np.array([r['medidas'][i][2] for r in res])
        print(f"{txt} | {ref:.2f} | {v.mean():.2f} | {v.min():.2f} | {v.max():.2f} | {100 * (v.mean() - ref):+.1f}")
    dpm = np.array([r['d_pm'].mean() for r in res])
    todos = np.concatenate([r['d_pm'] for r in res])
    print(f"\nDistancia media plano->mapa por iteración (cm): {np.round(100 * dpm, 2)}; media {100 * dpm.mean():.2f}; "
          f"todos los puntos: p95 {100 * np.percentile(todos, 95):.1f} cm")
    if len(dpm) > 1:
        from scipy import stats
        h = stats.t.ppf(0.975, len(dpm) - 1) * dpm.std(ddof=1) / np.sqrt(len(dpm))
        print(f"Intervalo de confianza al 95% de la distancia media: {100 * (dpm.mean() - h):.2f} a {100 * (dpm.mean() + h):.2f} cm")
    figura(res, nombres, os.path.join(a.salida, 'mapas_vs_plano.png'))
    print('Figura:', os.path.join(a.salida, 'mapas_vs_plano.png'))

if __name__ == '__main__':
    main()
