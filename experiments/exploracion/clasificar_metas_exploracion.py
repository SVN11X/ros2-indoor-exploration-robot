#!/usr/bin/env python3
"""
Clasifica las metas de exploracion a partir de explore_log_real.txt.

Uso:
  python3 clasificar_metas_exploracion.py test/sesiones_mapeo/sesion_actual 1 3 4 5 6

Lee el flujo de estado de /navigate_to_pose/_action/status que run_explore.sh
guarda con el prefijo "ACTION_STATUS". Para cada meta toma su identificador de
16 bytes, su sello de aceptacion y la secuencia de estados.

Una meta abortada se clasifica como "reemplazada" cuando existe un mensaje de
estado en el que la meta siguiente ya figura y la meta abortada sigue activa
(estado 1 o 2). Si la meta abortada nunca aparece activa junto a la siguiente,
queda "sin clasificar". Solo se usa el orden de los mensajes y los sellos de
aceptacion. No se usa la hora de escritura del registro.

Estados de action_msgs/GoalStatus: 1 aceptada, 2 en ejecucion, 3 cancelando,
4 exitosa, 5 cancelada, 6 abortada.
"""
import re
import statistics
import sys
from pathlib import Path


def leer_mensajes(ruta):
    mensajes, meta, modo = [], None, None
    for linea in open(ruta, encoding="utf-8", errors="replace"):
        m = re.match(r"\[[\d:]+\] ACTION_STATUS (.*)$", linea.rstrip("\r\n"))
        if not m:
            continue
        txt = m.group(1)
        limpio = txt.strip()
        if txt.startswith("status_list:"):
            mensajes.append([])
            meta = None
        elif not mensajes:
            continue
        elif txt.startswith("- goal_info:"):
            meta = {"uuid": [], "sec": 0, "ns": 0, "st": None}
            mensajes[-1].append(meta)
            modo = None
        elif meta is None:
            continue
        elif limpio in ("uuid:", "stamp:"):
            modo = limpio[:-1]
        elif modo == "uuid" and re.fullmatch(r"- \d+", limpio):
            meta["uuid"].append(int(limpio[2:]))
        elif limpio.startswith("sec: "):
            meta["sec"] = int(limpio[5:])
        elif limpio.startswith("nanosec: "):
            meta["ns"] = int(limpio[9:])
        elif txt.startswith("  status: "):
            meta["st"] = int(limpio[8:])
    return [
        {tuple(g["uuid"]): (g["st"], g["sec"] + g["ns"] * 1e-9)
         for g in msg if len(g["uuid"]) == 16 and g["st"] is not None}
        for msg in mensajes
    ]


def analizar(ruta):
    seq = leer_mensajes(ruta)
    sello = {}
    for msg in seq:
        for k, (_, t) in msg.items():
            sello.setdefault(k, t)
    orden = sorted(sello, key=sello.get)

    def estado_final(k):
        finales = [msg[k][0] for msg in seq if k in msg and msg[k][0] in (4, 5, 6)]
        return finales[0] if finales else None

    final = {k: estado_final(k) for k in orden}
    reemplazadas, sin_clasificar, tiempos = 0, 0, []
    for i, k in enumerate(orden):
        if final[k] != 6:
            continue
        sig = orden[i + 1] if i + 1 < len(orden) else None
        juntas = sig is not None and any(
            k in msg and sig in msg and msg[k][0] in (1, 2) for msg in seq)
        if juntas:
            reemplazadas += 1
            tiempos.append(sello[sig] - sello[k])
        else:
            sin_clasificar += 1

    texto = open(ruta, encoding="utf-8", errors="replace").read()
    return {
        "metas": len(orden),
        "abortadas": sum(v == 6 for v in final.values()),
        "exitosas": sum(v == 4 for v in final.values()),
        "sin_terminal": sum(v is None for v in final.values()),
        "reemplazadas": reemplazadas,
        "sin_clasificar": sin_clasificar,
        "t_mediano": statistics.median(tiempos) if tiempos else float("nan"),
        "t_max": max(tiempos) if tiempos else float("nan"),
        "fin_sin_fronteras": "No frontiers found, stopping" in texto,
    }


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    sesion = Path(sys.argv[1])
    total = dict.fromkeys(("metas", "abortadas", "reemplazadas",
                           "sin_clasificar", "exitosas", "sin_terminal"), 0)
    print("% Iter & Metas & Abortadas & Reemplazadas & Sin clasificar & "
          "Exitosas & Sin estado terminal & Tiempo activo mediano (s) & "
          "Tiempo activo maximo (s) & Termino sin fronteras")
    for it in sys.argv[2:]:
        ruta = sesion / f"iteracion_{int(it):02d}" / "exploracion" / "explore_log_real.txt"
        r = analizar(ruta)
        for c in total:
            total[c] += r[c]
        print(f"{int(it)} & {r['metas']} & {r['abortadas']} & {r['reemplazadas']} & "
              f"{r['sin_clasificar']} & {r['exitosas']} & {r['sin_terminal']} & "
              f"{r['t_mediano']:.1f} & {r['t_max']:.1f} & "
              f"{'Sí' if r['fin_sin_fronteras'] else 'No'} \\\\")
    print(f"Total & {total['metas']} & {total['abortadas']} & {total['reemplazadas']} & "
          f"{total['sin_clasificar']} & {total['exitosas']} & {total['sin_terminal']} & "
          f"--- & --- & --- \\\\")


if __name__ == "__main__":
    main()
