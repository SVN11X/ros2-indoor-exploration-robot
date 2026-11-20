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
    parser.add_argument("--duracion", type=float, default=60.0)
    parser.add_argument("--salida", type=str, required=True)
    args = parser.parse_args()

    rclpy.init()
    node = rclpy.create_node("medir_bloqueo_lidar")
    msgs = []
    t_recv = []
    node.create_subscription(
        LaserScan, "/scan",
        lambda m: (msgs.append(m), t_recv.append(time.time())),
        qos_profile_sensor_data,
    )

    t0 = time.time()
    print(f"  Capturando {args.duracion:.0f}s...", flush=True)
    deadline = t0 + args.duracion
    last_announce = t0
    while time.time() < deadline:
        rclpy.spin_once(node, timeout_sec=0.1)
        if time.time() - last_announce >= 5.0:
            elapsed = time.time() - t0
            print(f"  ... {elapsed:.0f}s / {args.duracion:.0f}s "
                  f"({len(msgs)} scans)", flush=True)
            last_announce = time.time()
    print(f"  Captura completa: {len(msgs)} scans", flush=True)

    if len(msgs) < 10:
        print(f"  ERROR: muy pocos scans capturados ({len(msgs)}).", flush=True)
        rclpy.shutdown()
        sys.exit(1)

    with open(args.salida, "w") as f:
        f.write("t_rel,n_total,n_validos,n_inf,n_muy_cerca,mediana_range\n")
        for t, m in zip(t_recv, msgs):
            t_rel = t - t0
            n_tot = len(m.ranges)
            validos = [r for r in m.ranges if math.isfinite(r) and r > 0]
            n_val = len(validos)
            n_inf = sum(1 for r in m.ranges if not math.isfinite(r))
            n_cerca = sum(1 for r in validos if r < 0.30)
            mediana = statistics.median(validos) if validos else 0.0
            f.write(f"{t_rel:.3f},{n_tot},{n_val},{n_inf},{n_cerca},{mediana:.3f}\n")

    rclpy.shutdown()

if __name__ == "__main__":
    main()