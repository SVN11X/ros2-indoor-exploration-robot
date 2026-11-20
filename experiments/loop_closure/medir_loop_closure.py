#!/usr/bin/env python3
import argparse
import math
import signal
import sys
import time

import rclpy
from rclpy.time import Time
from tf2_ros import Buffer, TransformListener

def yaw_from_quat(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)

running = True

def handler(signum, frame):
    global running
    running = False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--salida", type=str, required=True)
    parser.add_argument("--periodo", type=float, default=0.5)
    args = parser.parse_args()

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)

    rclpy.init()
    node = rclpy.create_node("medir_loop_closure")
    buf = Buffer()
    _lst = TransformListener(buf, node)

    print("  Esperando TFs...", flush=True)
    for _ in range(30):
        rclpy.spin_once(node, timeout_sec=0.2)
        try:
            buf.lookup_transform("odom", "base_link", Time())
            buf.lookup_transform("map", "base_link", Time())
            print("  TFs disponibles, REGISTRANDO...", flush=True)
            break
        except Exception:
            continue
    else:
        print("  ERROR: TFs no disponibles", flush=True)
        rclpy.shutdown()
        sys.exit(1)

    with open(args.salida, "w") as f:
        f.write("t_rel,odom_x,odom_y,odom_yaw,map_x,map_y,map_yaw\n")
        t0 = time.time()
        next_sample = t0
        last_announce = t0
        while running:
            rclpy.spin_once(node, timeout_sec=0.05)
            if time.time() < next_sample:
                continue
            t_rel = time.time() - t0
            try:
                t_odom = buf.lookup_transform("odom", "base_link", Time())
                t_map = buf.lookup_transform("map", "base_link", Time())
                ox = t_odom.transform.translation.x
                oy = t_odom.transform.translation.y
                oyaw = yaw_from_quat(t_odom.transform.rotation)
                mx = t_map.transform.translation.x
                my = t_map.transform.translation.y
                myaw = yaw_from_quat(t_map.transform.rotation)
                f.write(f"{t_rel:.2f},{ox:.4f},{oy:.4f},{oyaw:.4f},"
                        f"{mx:.4f},{my:.4f},{myaw:.4f}\n")
            except Exception:
                pass
            next_sample += args.periodo

            if time.time() - last_announce >= 5.0:
                print(f"  ... t={t_rel:.0f}s", flush=True)
                last_announce = time.time()

    print(f"  Registro detenido. t_total = {time.time() - t0:.1f} s", flush=True)
    rclpy.shutdown()

if __name__ == "__main__":
    main()