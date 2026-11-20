#!/usr/bin/env python3
import argparse
import statistics
import sys
import time

import rclpy
from nav_msgs.msg import Odometry
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--duracion", type=float, default=20.0)
    parser.add_argument("--salida", type=str, required=True)
    args = parser.parse_args()

    rclpy.init()
    node = rclpy.create_node("medir_stress")

    t_scan = []
    t_odom = []

    node.create_subscription(
        LaserScan, "/scan",
        lambda m: t_scan.append(time.time()),
        qos_profile_sensor_data,
    )
    node.create_subscription(
        Odometry, "/odom",
        lambda m: t_odom.append(time.time()),
        10,
    )

    print(f"  Midiendo {args.duracion:.0f}s...", flush=True)
    end = time.time() + args.duracion
    while time.time() < end:
        rclpy.spin_once(node, timeout_sec=0.05)
    print(f"  Recibidos: /scan={len(t_scan)} msgs | /odom={len(t_odom)} msgs", flush=True)

    if len(t_scan) < 5 or len(t_odom) < 5:
        print("  ERROR: muy pocos mensajes", flush=True)
        rclpy.shutdown()
        sys.exit(1)

    def periodos(ts):
        return [ts[i+1] - ts[i] for i in range(len(ts) - 1)]

    p_scan = periodos(t_scan)
    p_odom = periodos(t_odom)

    with open(args.salida, "w") as f:
        f.write("topic,freq_hz,periodo_ms_mean,periodo_ms_std,periodo_ms_min,periodo_ms_max,n_msgs\n")
        f.write(f"/scan,{1.0/statistics.mean(p_scan):.4f},"
                f"{statistics.mean(p_scan)*1000:.2f},"
                f"{statistics.stdev(p_scan)*1000:.2f},"
                f"{min(p_scan)*1000:.2f},{max(p_scan)*1000:.2f},"
                f"{len(t_scan)}\n")
        f.write(f"/odom,{1.0/statistics.mean(p_odom):.4f},"
                f"{statistics.mean(p_odom)*1000:.2f},"
                f"{statistics.stdev(p_odom)*1000:.2f},"
                f"{min(p_odom)*1000:.2f},{max(p_odom)*1000:.2f},"
                f"{len(t_odom)}\n")

    f_scan = 1.0 / statistics.mean(p_scan)
    f_odom = 1.0 / statistics.mean(p_odom)
    print(f"  /scan: {f_scan:.2f} Hz  | std={statistics.stdev(p_scan)*1000:.1f} ms", flush=True)
    print(f"  /odom: {f_odom:.2f} Hz  | std={statistics.stdev(p_odom)*1000:.1f} ms", flush=True)

    rclpy.shutdown()

if __name__ == "__main__":
    main()