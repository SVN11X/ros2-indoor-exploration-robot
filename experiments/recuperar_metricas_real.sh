#!/usr/bin/env bash
# ============================================================================
#  recuperar_metricas_real.sh
#  Recupera, de forma post-hoc y SIN mover el robot, las métricas de mapeo
#  real de TODAS las iteraciones de una sesión de exploración.
#
#  Por cada iteracion_NN/ con rosbag:
#   [A] Núcleo fiable (siempre): distancia odométrica, cobertura y área del
#       PGM, duración y resolución  ->  via analizar_slam.py
#   [B] Reconstrucción offline (opcional, --with-slam): nº de nodos del grafo
#       y detección de cierre de lazo, reproduciendo el rosbag por
#       slam_toolbox. Se marca como RECONSTRUCCIÓN, no como medición en vivo.
#
#  Agrega todo en:
#     <SESION>/_analisis_post/resumen_slam_real_todas.csv
#     <SESION>/_analisis_post/tabla_slam_real_por_iteracion.tex   (paste-ready)
#
#  Uso:
#     bash recuperar_metricas_real.sh [RUTA_SESION] [--with-slam|--no-slam]
#  Por defecto RUTA_SESION = autodetect de 'sesiones_mapeo/sesion_actual'.
# ============================================================================

set -uo pipefail   # NO -e: queremos continuar aunque una iteración falle

# ---------------------------------------------------------------------------
# 0. Configuración y argumentos
# ---------------------------------------------------------------------------
SESION_ARG=""
WITH_SLAM="auto"          # auto | yes | no
SLAM_LAUNCH="${SLAM_LAUNCH:-slam_toolbox online_async_launch.py}"
SLAM_SETTLE_S="${SLAM_SETTLE_S:-12}"    # espera a que slam_toolbox arranque
PLAY_RATE="${PLAY_RATE:-1.0}"           # velocidad de reproducción del bag

for a in "$@"; do
  case "$a" in
    --with-slam) WITH_SLAM="yes" ;;
    --no-slam)   WITH_SLAM="no"  ;;
    -h|--help)   grep '^#' "$0" | sed 's/^# \?//'; exit 0 ;;
    *)           SESION_ARG="$a" ;;
  esac
done

log()  { printf '%s\n' "$*"; }
hr()   { printf '%s\n' "────────────────────────────────────────────────────────────"; }

# ---------------------------------------------------------------------------
# 1. Localizar la sesión y analizar_slam.py
# ---------------------------------------------------------------------------
buscar_sesion() {
  if [ -n "$SESION_ARG" ] && [ -d "$SESION_ARG" ]; then
    ( cd "$SESION_ARG" && pwd ); return
  fi
  local d; d="$(pwd)"
  for _ in $(seq 1 8); do
    if [ -d "$d/sesiones_mapeo/sesion_actual" ]; then
      echo "$d/sesiones_mapeo/sesion_actual"; return
    fi
    if [ -d "$d/sesion_actual" ]; then echo "$d/sesion_actual"; return; fi
    [ "$(basename "$d")" = "sesion_actual" ] && { echo "$d"; return; }
    d="$(dirname "$d")"; [ "$d" = "/" ] && break
  done
  echo ""
}

SESION="$(buscar_sesion)"
if [ -z "$SESION" ] || [ ! -d "$SESION" ]; then
  log "ERROR: no se encontró la carpeta de sesión."
  log "       Pásala como primer argumento: bash $0 /ruta/a/sesion_actual"
  exit 1
fi

ANALIZAR="$(find "$SESION/../.." -name analizar_slam.py 2>/dev/null | head -1)"
[ -z "$ANALIZAR" ] && ANALIZAR="$(find "$HOME" -name analizar_slam.py 2>/dev/null | head -1)"
if [ -z "$ANALIZAR" ]; then
  log "ERROR: no se encontró analizar_slam.py"; exit 1
fi

OUTROOT="$SESION/_analisis_post"
mkdir -p "$OUTROOT"

# ¿Hay ROS disponible?
# Sourcear ROS y/o workspace si se indican por variable de entorno
# (necesario para --with-slam). Ej.:
#   ROS_SETUP=/opt/ros/foxy/setup.bash \
#   WS_SETUP=~/tesis_black_robot/install/setup.bash \
#   bash recuperar_metricas_real.sh --with-slam
for _s in "${ROS_SETUP:-}" "${WS_SETUP:-}"; do
  [ -z "$_s" ] && continue
  # expandir ~ manualmente por si viene literal
  _s="${_s/#\~/$HOME}"
  if [ -f "$_s" ]; then
    # shellcheck disable=SC1090
    source "$_s" && log "  Sourced: $_s"
  else
    log "  AVISO: no existe el setup indicado: $_s"
  fi
done
HAVE_ROS="no"; command -v ros2 >/dev/null 2>&1 && HAVE_ROS="yes"
if [ "$WITH_SLAM" = "auto" ]; then
  [ "$HAVE_ROS" = "yes" ] && WITH_SLAM="yes" || WITH_SLAM="no"
fi
if [ "$WITH_SLAM" = "yes" ] && [ "$HAVE_ROS" = "no" ]; then
  log "AVISO: se pidió --with-slam pero no hay 'ros2' en el PATH. Se omite la fase SLAM."
  WITH_SLAM="no"
fi

hr
log "  Sesión        : $SESION"
log "  analizar_slam : $ANALIZAR"
log "  Salida        : $OUTROOT"
log "  Fase SLAM     : $WITH_SLAM (reconstrucción offline de nodos/cierre de lazo)"
hr

# ---------------------------------------------------------------------------
# 2. Fase SLAM (reconstrucción offline por iteración) — best effort
# ---------------------------------------------------------------------------
reconstruir_slam() {
  # $1 = ruta del rosbag (carpeta con metadata.yaml)  $2 = etiqueta (iterNN)
  # Escribe "$OUTROOT/<etiqueta>_extra.csv" con: nodos,cierre
  local bag="$1" etq="$2"
  local logf="$OUTROOT/${etq}_slam_replay.log"
  local extra="$OUTROOT/${etq}_extra.csv"
  echo "nodos,cierre" > "$extra"

  log "    [B] Reconstrucción SLAM offline ($etq)…"
  # Lanzar slam_toolbox. En Foxy, 'ros2 bag play' no publica /clock (no existe
  # --clock), así que se usa use_sim_time:=false y se reproduce con stamps del bag.
  ( ros2 launch $SLAM_LAUNCH use_sim_time:=false ) >"$logf" 2>&1 &
  local slam_pid=$!
  sleep "$SLAM_SETTLE_S"

  if ! kill -0 "$slam_pid" 2>/dev/null; then
    log "    AVISO: slam_toolbox no arrancó; nodos/cierre quedan '---'."
    log "    --- últimas líneas de $(basename "$logf") ---"
    tail -n 12 "$logf" 2>/dev/null | sed 's/^/      /'
    return
  fi

  # Muestreador de nodos en 2º plano: durante el replay guarda el MÁXIMO de
  # marcadores observado en /slam_toolbox/graph_visualization (el grafo crece).
  local nodos_file="$OUTROOT/${etq}_nodos.tmp"; echo 0 > "$nodos_file"
  ( for _ in $(seq 1 80); do
      n=$(timeout 4 ros2 topic echo --once /slam_toolbox/graph_visualization \
            2>/dev/null | grep -cE '^[[:space:]]*-[[:space:]]*header:')
      cur=$(cat "$nodos_file" 2>/dev/null || echo 0)
      [ "${n:-0}" -gt "${cur:-0}" ] && echo "$n" > "$nodos_file"
      sleep 3
    done ) &
  local samp_pid=$!

  # Reproducir el bag (Foxy: SIN --clock). slam_toolbox procesa /scan + /tf.
  ros2 bag play "$bag" -r "$PLAY_RATE" >>"$logf" 2>&1
  sleep 5

  kill "$samp_pid" 2>/dev/null
  local nodos="---"
  local mk; mk="$(cat "$nodos_file" 2>/dev/null || echo 0)"
  [ "${mk:-0}" -gt 0 ] && nodos="$mk"
  rm -f "$nodos_file"

  # Serializar el grafo como respaldo (queda el .posegraph para inspección)
  timeout 15 ros2 service call /slam_toolbox/serialize_map \
        slam_toolbox/srv/SerializePoseGraph \
        "{filename: '$OUTROOT/${etq}_posegraph'}" >>"$logf" 2>&1 || true

  # Cierre de lazo: buscar eventos en el log de slam_toolbox
  local cierre="No detectado"
  if grep -qiE 'loop clos|loop-clos|closing loop|añadiendo cierre' "$logf"; then
    cierre="Sí"
  fi

  # Detener slam_toolbox
  kill "$slam_pid" 2>/dev/null; sleep 2; kill -9 "$slam_pid" 2>/dev/null || true

  echo "${nodos},${cierre}" >> "$extra"
  log "    [B] nodos=$nodos  cierre=$cierre  (reconstrucción)"
}

# ---------------------------------------------------------------------------
# 3. Bucle principal sobre todas las iteraciones
# ---------------------------------------------------------------------------
shopt -s nullglob
ITERS=( "$SESION"/iteracion_* )
if [ "${#ITERS[@]}" -eq 0 ]; then
  log "ERROR: no hay carpetas iteracion_* en $SESION"; exit 1
fi
IFS=$'\n' ITERS=( $(printf '%s\n' "${ITERS[@]}" | sort) ); unset IFS

log "  Iteraciones encontradas: ${#ITERS[@]}"
hr

for IT in "${ITERS[@]}"; do
  ETQ="$(basename "$IT" | sed 's/iteracion_/iter/')"
  log "▶ $(basename "$IT")  [$ETQ]"

  BAG="$(find "$IT" -path '*rosbag*' -name metadata.yaml -printf '%h\n' 2>/dev/null | head -1)"
  PGM="$(find "$IT" -name '*.pgm' 2>/dev/null | head -1)"
  OUT="$IT/analisis_post"; mkdir -p "$OUT"

  if [ -z "$BAG" ]; then
    log "    SIN rosbag -> iteración no procesable (se marca abortada)."
    echo "indicador,valor,unidad" > "$OUT/slam_metricas_${ETQ}.csv"
    echo "estado,abortada," >> "$OUT/slam_metricas_${ETQ}.csv"
    continue
  fi
  log "    Bag: $BAG"
  [ -n "$PGM" ] && log "    PGM: $PGM" || log "    PGM: (ausente — solo distancia/duración)"

  # [A] Núcleo fiable
  if [ -n "$PGM" ]; then
    python3 "$ANALIZAR" --modo real --bag "$BAG" --pgm "$PGM" \
            --out "$OUT" --suffix "$ETQ" || \
      log "    AVISO: analizar_slam.py falló en $ETQ"
  else
    python3 "$ANALIZAR" --modo real --bag "$BAG" \
            --out "$OUT" --suffix "$ETQ" || \
      log "    AVISO: analizar_slam.py falló en $ETQ"
  fi
  # copiar el csv al pozo común para la agregación
  [ -f "$OUT/slam_metricas_${ETQ}.csv" ] && \
     cp "$OUT/slam_metricas_${ETQ}.csv" "$OUTROOT/" 2>/dev/null || true

  # [B] Reconstrucción SLAM offline
  if [ "$WITH_SLAM" = "yes" ]; then
    reconstruir_slam "$BAG" "$ETQ"
  fi
  hr
done

# ---------------------------------------------------------------------------
# 4. Agregación -> CSV resumen + tabla LaTeX (paste-ready)
# ---------------------------------------------------------------------------
log "Agregando resultados…"
python3 - "$OUTROOT" <<'PYEOF'
import csv, glob, os, sys, statistics as st

outroot = sys.argv[1]

def load(path):
    d = {}
    try:
        with open(path, newline='') as f:
            for row in csv.reader(f):
                if len(row) >= 2 and row[0] not in ('indicador',''):
                    d[row[0].strip()] = row[1].strip()
    except FileNotFoundError:
        pass
    return d

rows = []
for csvp in sorted(glob.glob(os.path.join(outroot, 'slam_metricas_iter*.csv'))):
    etq = os.path.basename(csvp).replace('slam_metricas_','').replace('.csv','')
    m = load(csvp)
    extra = load(os.path.join(outroot, f'{etq}_extra.csv'))  # nodos,cierre (formato distinto)
    # _extra.csv tiene cabecera nodos,cierre y una fila de valores
    nodos, cierre = '---', '---'
    ep = os.path.join(outroot, f'{etq}_extra.csv')
    if os.path.exists(ep):
        with open(ep, newline='') as f:
            r = list(csv.reader(f))
            if len(r) >= 2 and len(r[1]) >= 2:
                nodos, cierre = r[1][0].strip() or '---', r[1][1].strip() or '---'
    estado = m.get('estado', 'ok')
    area   = m.get('area_libre', '---')
    cob    = m.get('cobertura', '---')
    # Sin PGM (area '---') => iteración incompleta: cobertura/área no disponibles
    if estado != 'abortada' and str(area).strip() in ('---', '', 'None'):
        estado = 'incompleta'
        cob, area = '---', '---'
    rows.append({
        'iteracion': etq.replace('iter','').lstrip('0') or '0',
        'estado'   : estado,
        'duracion' : m.get('duracion','---'),
        'distancia': m.get('distancia_odom','---'),
        'cobertura': cob,
        'area'     : area,
        'resol'    : m.get('resolucion','---'),
        'nodos'    : nodos,
        'cierre'   : cierre,
    })

# --- CSV resumen ---
res_csv = os.path.join(outroot, 'resumen_slam_real_todas.csv')
campos = ['iteracion','estado','duracion','distancia','cobertura','area','resol','nodos','cierre']
with open(res_csv, 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=campos); w.writeheader()
    for r in rows: w.writerow(r)

# --- estadísticos sobre iteraciones válidas ---
def fnums(key):
    out = []
    for r in rows:
        if r['estado'] in ('abortada', 'incompleta'): continue
        try: out.append(float(r[key]))
        except (ValueError, TypeError): pass
    return out

def musig(key):
    v = fnums(key)
    if not v: return ('---','---')
    mu = st.mean(v)
    sg = st.stdev(v) if len(v) > 1 else 0.0
    return (f'{mu:.2f}', f'{sg:.2f}')

# --- tabla LaTeX paste-ready ---
def cell(x):
    return x if x not in (None,'','None') else '---'

tex = os.path.join(outroot, 'tabla_slam_real_por_iteracion.tex')
L = []
L.append('% Generado por recuperar_metricas_real.sh')
L.append('% Núcleo (duración, distancia, cobertura, área) = recuperado del rosbag/PGM.')
L.append('% Nodos y cierre de lazo = reconstrucción offline por replay en slam_toolbox.')
L.append(r'\begin{table}[H]')
L.append(r'\centering')
L.append(r"\caption{Indicadores de mapeo real por iteración, recuperados post-hoc del rosbag y el mapa PGM. Los nodos del grafo y el cierre de lazo provienen de una reconstrucción offline reproduciendo el rosbag en \texttt{slam\_toolbox}.}")
L.append(r'\label{tab:slam_real_por_iteracion}')
L.append(r'\small')
L.append(r'\begin{tabular}{c c c c c c c}')
L.append(r'\toprule')
L.append(r"\textbf{Iter.} & \textbf{Dur. (min)} & \textbf{Dist. odom. (m)} & \textbf{Cobertura PGM (\%)} & \textbf{Área libre (m\textsuperscript{2})} & \textbf{Nodos*} & \textbf{Cierre lazo*} \\")
L.append(r'\midrule')
for r in rows:
    if r['estado'] in ('abortada', 'incompleta'):
        etiqueta = 'Abortada' if r['estado'] == 'abortada' else 'Incompleta (sin mapa)'
        L.append(f"{r['iteracion']} & \\multicolumn{{6}}{{c}}{{{etiqueta}}} \\\\")
        continue
    L.append(' & '.join([
        r['iteracion'], cell(r['duracion']), cell(r['distancia']),
        cell(r['cobertura']), cell(r['area']), cell(r['nodos']), cell(r['cierre']),
    ]) + r' \\')
L.append(r'\midrule')
mu_d, sg_d = musig('duracion'); mu_x, sg_x = musig('distancia')
mu_c, sg_c = musig('cobertura'); mu_a, sg_a = musig('area')
L.append(f"$\\mu$ & {mu_d} & {mu_x} & {mu_c} & {mu_a} & --- & --- \\\\")
L.append(f"$\\sigma$ & {sg_d} & {sg_x} & {sg_c} & {sg_a} & --- & --- \\\\")
L.append(r'\bottomrule')
L.append(r'\end{tabular}')
L.append(r"\\[2pt] {\footnotesize * Reconstrucción offline a partir del rosbag; no es una medición de la sesión en vivo.}")
L.append(r'\end{table}')
with open(tex, 'w') as f:
    f.write('\n'.join(L) + '\n')

print(f"  ✓ {res_csv}")
print(f"  ✓ {tex}")
print(f"  Iteraciones agregadas: {len(rows)}")
PYEOF

hr
log "LISTO."
log "  Resumen CSV : $OUTROOT/resumen_slam_real_todas.csv"
log "  Tabla LaTeX : $OUTROOT/tabla_slam_real_por_iteracion.tex"
log ""
log "Pégame el contenido de esos dos archivos y te devuelvo los bloques"
log "buscar->reemplazar finales para el anexo, con valores reales (sin inventar)."