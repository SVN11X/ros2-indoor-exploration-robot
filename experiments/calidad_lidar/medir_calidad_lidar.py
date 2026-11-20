#!/usr/bin/env python3
import argparse
import math
import statistics
import sys
import time

import rclpy
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duracion", type=float, default=20.0,
                        help="Duración de la captura en segundos")
    parser.add_argument("--salida", type=str, required=True,
                        help="Archivo CSV de salida")
    parser.add_argument("--prueba", type=int, default=1)
    args = parser.parse_args()

    rclpy.init()
    node = rclpy.create_node("medir_calidad_lidar")

    msgs = []
    t_recv = []
    node.create_subscription(
        LaserScan, "/scan",
        lambda m: (msgs.append(m), t_recv.append(time.time())),
        qos_profile_sensor_data,
    )

    print(f"  [Prueba {args.prueba}] Capturando {args.duracion:.0f}s...", flush=True)
    deadline = time.time() + args.duracion
    while time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
    print(f"  [Prueba {args.prueba}] Capturados {len(msgs)} scans", flush=True)

    if len(msgs) < 5:
        print(f"  ERROR: muy pocos scans capturados ({len(msgs)}).", flush=True)
        rclpy.shutdown()
        sys.exit(1)

    with open(args.salida, "w") as f:
        f.write("t_recv,n_total,n_validos,n_inf,span_rad,ang_inc,range_min_obs,range_max_obs\n")
        for t, m in zip(t_recv, msgs):
            n_tot = len(m.ranges)
            validos = [r for r in m.ranges if math.isfinite(r) and r > 0]
            n_val = len(validos)
            n_inf = sum(1 for r in m.ranges if not math.isfinite(r))
            span = m.angle_max - m.angle_min
            ainc = m.angle_increment
            rmin = min(validos) if validos else 0.0
            rmax = max(validos) if validos else 0.0
            f.write(f"{t:.6f},{n_tot},{n_val},{n_inf},{span:.6f},{ainc:.6f},{rmin:.4f},{rmax:.4f}\n")

    periods = [t_recv[i+1] - t_recv[i] for i in range(len(t_recv)-1)]
    freq = 1.0 / statistics.mean(periods)
    n_val_avg = statistics.mean([sum(1 for r in m.ranges if math.isfinite(r) and r > 0) for m in msgs])
    print(f"  [Prueba {args.prueba}] freq={freq:.2f} Hz | puntos válidos medios={n_val_avg:.0f}", flush=True)

    rclpy.shutdown()

if __name__ == "__main__":
    main()