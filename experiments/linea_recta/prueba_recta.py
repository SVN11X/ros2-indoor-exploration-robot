#!/usr/bin/env python3
"""
Prueba de trayectoria rectilínea (2 m a 0.13 m/s).
Uso: python3 prueba_recta.py --prueba 1
Genera: prueba_recta_N.log con xi, yi, xf, yf, dist_odom
"""
import argparse
import math
import time
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
import os

VEL_LINEAL   = 0.13          # m/s — igual a max_velocity en mycontrollers.yaml
DIST_TEORICA = 2.00          # m
DURACION     = DIST_TEORICA / VEL_LINEAL   # ~13.33 s
TOPIC_CMD    = "diff_cont/cmd_vel_unstamped"
TOPIC_ODOM   = "odom"
FREQ_HZ      = 20            # Hz del timer de control
COUNTDOWN    = 5             # segundos de cuenta regresiva antes de moverse
SETTLE_TIME  = 2.0           # segundos esperando que el robot se detenga completamente
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


class PruebaRectaNode(Node):
    def __init__(self, num_prueba: int):
        super().__init__("prueba_recta")
        self.num_prueba = num_prueba
        self.xi = self.yi = None
        self.xf = self.yf = None
        self.fase = "esperar_odom"      # esperar_odom → countdown → mover → frenar → leer_final → done
        self._finished  = False         # FIX: flag para salir del spin
        self.t_inicio   = None
        self.t_frenar   = None
        self.t_cuenta   = None
        self.cuenta_ant = -1

        self.pub_cmd  = self.create_publisher(Twist, TOPIC_CMD, 10)
        self.sub_odom = self.create_subscription(Odometry, TOPIC_ODOM, self.odom_cb, 10)
        self.timer    = self.create_timer(1.0 / FREQ_HZ, self.loop)

        self.get_logger().info(f"Prueba {num_prueba} | v={VEL_LINEAL} m/s | "
                               f"t={DURACION:.2f} s | dist_teórica={DIST_TEORICA} m")
        self.get_logger().info(f"Esperando primer mensaje de {TOPIC_ODOM}...")

    # ── callbacks ────────────────────────────────────────────────────────────
    def odom_cb(self, msg: Odometry):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y

        if self.fase == "esperar_odom":
            # Solo guardamos posición para mostrarla; fase sigue igual
            self._last_x, self._last_y = x, y

        elif self.fase == "leer_final":
            self.xf, self.yf = x, y

    # ── loop principal ───────────────────────────────────────────────────────
    def loop(self):
        cmd = Twist()

        if self.fase == "esperar_odom":
            if not hasattr(self, "_last_x"):
                return
            # Primer odom recibido → iniciar countdown
            self.get_logger().info(
                f"  /odom OK — posición actual: "
                f"x={self._last_x:.4f} y={self._last_y:.4f}")
            self.get_logger().info(
                f">>> ALINEA el robot con la marca de inicio. "
                f"Movimiento en {COUNTDOWN} s...")
            self.t_cuenta = time.time()
            self.fase = "countdown"

        elif self.fase == "countdown":
            restante = int(COUNTDOWN - (time.time() - self.t_cuenta))
            if restante != self.cuenta_ant and restante > 0:
                self.get_logger().info(f"  {restante}...")
                self.cuenta_ant = restante
            if time.time() - self.t_cuenta >= COUNTDOWN:
                # Grabar posición inicial JUSTO antes de arrancar
                self.xi, self.yi = self._last_x, self._last_y
                self.get_logger().info(
                    f"INICIO → xi={self.xi:.4f} m  yi={self.yi:.4f} m")
                self.t_inicio = time.time()
                self.fase = "mover"

        elif self.fase == "mover":
            elapsed = time.time() - self.t_inicio
            if elapsed < DURACION:
                cmd.linear.x = VEL_LINEAL
                self.pub_cmd.publish(cmd)
                # log cada segundo
                seg = int(elapsed)
                if seg != getattr(self, "_seg_ant", -1):
                    self.get_logger().info(
                        f"  t={elapsed:.1f}/{DURACION:.1f} s")
                    self._seg_ant = seg
            else:
                self.pub_cmd.publish(Twist())   # parada
                self.get_logger().info("Comando de parada enviado.")
                self.t_frenar = time.time()
                self.fase = "frenar"

        elif self.fase == "frenar":
            self.pub_cmd.publish(Twist())       # mantener velocidad cero
            if time.time() - self.t_frenar >= SETTLE_TIME:
                self.get_logger().info("Leyendo posición final...")
                self.fase = "leer_final"

        elif self.fase == "leer_final":
            if self.xf is not None:
                self._calcular_y_reportar()
                self.fase = "done"
                self.timer.cancel()
                # FIX: usar flag en vez de rclpy.shutdown() dentro de callback
                self._finished = True

    # ── reporte y log ────────────────────────────────────────────────────────
    def _calcular_y_reportar(self):
        dist_odom = math.sqrt((self.xf - self.xi)**2 + (self.yf - self.yi)**2)
        sep = "=" * 55
        self.get_logger().info(sep)
        self.get_logger().info(f"PRUEBA {self.num_prueba} — RESULTADOS")
        self.get_logger().info(sep)
        self.get_logger().info(f"  Pos. inicial : x={self.xi:.4f}  y={self.yi:.4f} m")
        self.get_logger().info(f"  Pos. final   : x={self.xf:.4f}  y={self.yf:.4f} m")
        self.get_logger().info(f"  Dist. teórica: {DIST_TEORICA:.3f} m")
        self.get_logger().info(f"  Dist. odom   : {dist_odom:.4f} m")
        self.get_logger().info(sep)
        self.get_logger().info(
            ">>> Mide con cinta métrica la distancia REAL y anótala.")
        self.get_logger().info(
            f"    Error (%) = |{dist_odom:.4f} - dist_real| / dist_real × 100")
        self.get_logger().info(sep)

        fname = os.path.join(SCRIPT_DIR, f"prueba_recta_{self.num_prueba}.log")
        with open(fname, "w") as f:
            f.write(f"prueba,{self.num_prueba}\n")
            f.write(f"dist_teorica,{DIST_TEORICA:.4f}\n")
            f.write(f"dist_odom,{dist_odom:.6f}\n")
            f.write(f"xi,{self.xi:.6f}\n")
            f.write(f"yi,{self.yi:.6f}\n")
            f.write(f"xf,{self.xf:.6f}\n")
            f.write(f"yf,{self.yf:.6f}\n")
        self.get_logger().info(f"Log guardado: {fname}")


def main():
    parser = argparse.ArgumentParser(
        description="Prueba de trayectoria rectilínea — odometría 2 m")
    parser.add_argument("--prueba", type=int, default=1,
                        help="Número de repetición (1-5)")
    args = parser.parse_args()

    rclpy.init()
    node = PruebaRectaNode(args.prueba)
    try:
        # FIX: spin_once loop para que _finished flag funcione en Foxy
        while rclpy.ok() and not getattr(node, "_finished", False):
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        node.get_logger().warn("Interrupción manual — enviando velocidad cero.")
        node.pub_cmd.publish(Twist())
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()