#!/usr/bin/env python3
import argparse
import csv
import math
import time
import os
from collections import defaultdict

import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan

class ScanStabilityAnalyzer(Node):
    def __init__(self, duration: float, label: str):
        super().__init__('scan_stability_analyzer')
        self.duration = duration
        self.label = label
        self.scans_data = []
        self.scan_count = 0
        self.n_bins = None
        self.t0 = time.time()

        self.sub = self.create_subscription(
            LaserScan, '/scan', self._cb, qos_profile_sensor_data
        )
        self.timer = self.create_timer(1.0, self._tick)
        self.get_logger().info(
            f'Recolectando scans durante {duration:.0f}s '
            f'(etiqueta="{label}")... robot debe estar QUIETO'
        )

    def _cb(self, msg: LaserScan):
        if self.n_bins is None:
            self.n_bins = len(msg.ranges)
            self.get_logger().info(f'Detectado N={self.n_bins} bins')

        valid = []
        for i, r in enumerate(msg.ranges):
            if math.isfinite(r) and msg.range_min <= r <= msg.range_max:
                valid.append((i, r))
        self.scans_data.append(valid)
        self.scan_count += 1

    def _tick(self):
        elapsed = time.time() - self.t0
        if elapsed >= self.duration:
            self._analyze()
            rclpy.shutdown()
        else:
            self.get_logger().info(
                f'[{elapsed:5.1f}s/{self.duration:.0f}s] '
                f'{self.scan_count} scans recibidos'
            )

    def _analyze(self):
        if self.scan_count == 0 or self.n_bins is None:
            self.get_logger().error('No se recibieron scans')
            return

        n_scans = self.scan_count
        hits_per_bin = [0] * self.n_bins
        ranges_per_bin = defaultdict(list)
        valid_per_scan = []

        for scan in self.scans_data:
            valid_per_scan.append(len(scan))
            for idx, r in scan:
                hits_per_bin[idx] += 1
                ranges_per_bin[idx].append(r)
        stable_bins      = sum(1 for h in hits_per_bin if h / n_scans >= 0.90)
        intermittent     = sum(1 for h in hits_per_bin if 0.30 <= h / n_scans < 0.90)
        sparse           = sum(1 for h in hits_per_bin if 0.0  <  h / n_scans < 0.30)
        empty            = sum(1 for h in hits_per_bin if h == 0)
        stddev_stable = []
        for idx, ranges in ranges_per_bin.items():
            if hits_per_bin[idx] / n_scans >= 0.90 and len(ranges) >= 2:
                mean = sum(ranges) / len(ranges)
                var  = sum((r - mean)**2 for r in ranges) / len(ranges)
                stddev_stable.append(math.sqrt(var))

        avg_valid     = sum(valid_per_scan) / n_scans
        pct_populated = 100.0 * avg_valid / self.n_bins
        stddev_med    = sorted(stddev_stable)[len(stddev_stable)//2] if stddev_stable else 0.0
        stddev_p95    = sorted(stddev_stable)[int(0.95*len(stddev_stable))] if stddev_stable else 0.0

        print('\n' + '='*60)
        print(f'  RESULTADOS — etiqueta: "{self.label}"')
        print('='*60)
        print(f'  Scans recolectados:           {n_scans}')
        print(f'  Bins configurados (N):        {self.n_bins}')
        print(f'  Bins poblados promedio:       {avg_valid:.1f} ({pct_populated:.1f}%)')
        print(f'  Bins estables (>=90%):        {stable_bins} ({100*stable_bins/self.n_bins:.1f}%)')
        print(f'  Bins intermitentes (30-90%):  {intermittent} ({100*intermittent/self.n_bins:.1f}%)')
        print(f'  Bins esporádicos (<30%):      {sparse} ({100*sparse/self.n_bins:.1f}%)')
        print(f'  Bins vacíos (0%):             {empty} ({100*empty/self.n_bins:.1f}%)')
        print(f'  Stddev range bins estables — mediana: {stddev_med*1000:.1f} mm')
        print(f'  Stddev range bins estables — p95:     {stddev_p95*1000:.1f} mm')
        print('='*60)
        latex_lines = [
            r'\begin{tabular}{lr}',
            r'\hline',
            r'Métrica & Valor \\',
            r'\hline',
            f'Scans analizados & {n_scans} \\\\',
            f'Bins configurados & {self.n_bins} \\\\',
            fr'Cobertura promedio & {pct_populated:.1f}\% \\',
            fr'Bins estables ($\geq$90\%) & {100*stable_bins/self.n_bins:.1f}\% \\',
            fr'Bins intermitentes (30--90\%) & {100*intermittent/self.n_bins:.1f}\% \\',
            fr'$\sigma$ range (mediana) & {stddev_med*1000:.1f} mm \\',
            fr'$\sigma$ range (percentil 95) & {stddev_p95*1000:.1f} mm \\',
            r'\hline',
            r'\end{tabular}',
        ]
        out_dir = os.path.dirname(os.path.abspath(__file__))
        tex_path = os.path.join(out_dir, f'tabla_scan_stability_{self.label}.tex')
        with open(tex_path, 'w') as f:
            f.write('\n'.join(latex_lines))
        print('\n--- LaTeX guardado ---')
        print(f'Archivo LaTeX: {tex_path}')
        out_dir = os.path.dirname(os.path.abspath(__file__))
        csv_path = os.path.join(out_dir, f'scan_stability_{self.label}.csv')
        with open(csv_path, 'w', newline='') as f:
            w = csv.writer(f)
            w.writerow(['bin_idx', 'hit_rate', 'mean_range_m', 'stddev_range_m', 'n_hits'])
            for idx in range(self.n_bins):
                hits = hits_per_bin[idx]
                ranges = ranges_per_bin.get(idx, [])
                if ranges:
                    mean = sum(ranges) / len(ranges)
                    var  = sum((r - mean)**2 for r in ranges) / len(ranges)
                    sd   = math.sqrt(var)
                else:
                    mean = sd = 0.0
                w.writerow([idx, hits/n_scans, mean, sd, hits])
        print(f'\nCSV exportado: {csv_path}')
        resumen_path = os.path.join(out_dir, f'scan_stability_resumen_{self.label}.txt')
        with open(resumen_path, 'w') as f:
            f.write(f'Resultados estabilidad scan - {self.label}\n')
            f.write('='*60 + '\n')
            f.write(f'Scans recolectados: {n_scans}\n')
            f.write(f'Bins configurados: {self.n_bins}\n')
            f.write(f'Cobertura promedio: {pct_populated:.1f}%\n')
            f.write(f'Bins estables >=90%: {100*stable_bins/self.n_bins:.1f}%\n')
            f.write(f'Bins intermitentes 30-90%: {100*intermittent/self.n_bins:.1f}%\n')
            f.write(f'Stddev range mediana: {stddev_med*1000:.1f} mm\n')
            f.write(f'Stddev range p95: {stddev_p95*1000:.1f} mm\n')
        print(f'Resumen exportado: {resumen_path}')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--duracion', type=float, default=60.0,
                    help='Segundos de recolección (default 60)')
    ap.add_argument('--etiqueta', type=str, default='test',
                    help='Etiqueta para CSV de salida')
    args = ap.parse_args()

    rclpy.init()
    node = ScanStabilityAnalyzer(args.duracion, args.etiqueta)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()