#!/usr/bin/env python3
"""
Prueba de giro completo (360° a 0.5 rad/s).
Uso: python3 prueba_giro.py --prueba 1
Genera: prueba_giro_N.log con yaw_inicial, yaw_final, delta_odom_deg
"""
import argparse
import math
import os
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry

VEL_ANGULAR   = 0.4                        # rad/s
GIRO_TEORICO  = 2 * math.pi               # rad  (360°)
DURACION      = GIRO_TEORICO / VEL_ANGULAR # ~12.566 s
TOPIC_CMD     = "diff_cont/cmd_vel_unstamped"
TOPIC_ODOM    = "odom"
FREQ_HZ       = 20
COUNTDOWN     = 5      # s de cuenta regresiva antes de girar
SETTLE_TIME   = 2.0    # s esperando que el robot se detenga
SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))


def quat_to_yaw(ox, oy, oz, ow) -> float:
    """Quaternion → yaw (rad), rango [-π, π]."""
    return math.atan2(2.0 * (ow * oz + ox * oy),
                      1.0 - 2.0 * (oy * oy + oz * oz))


def normalize_angle(a: float) -> float:
    """Normaliza un ángulo al rango [-π, π]."""
    while a >  math.pi: a -= 2 * math.pi
    while a < -math.pi: a += 2 * math.pi
    return a


class PruebaGiroNode(Node):
    def __init__(self, num_prueba: int):
        super().__init__("prueba_giro")
        self.num_prueba       = num_prueba
        self.fase             = "esperar_odom"
        self.t_inicio         = None
        self.t_frenar         = None
        self.t_cuenta         = None
        self.cuenta_ant       = -1
        self._finished        = False       # FIX: flag para salir del spin

        # Acumulación de yaw (robusto ante cruce de ±π)
        self.yaw_inicial      = None
        self.yaw_prev         = None
        self.yaw_acumulado    = 0.0   # rad, acumulado desde el inicio del giro

        self.pub_cmd  = self.create_publisher(Twist, TOPIC_CMD, 10)
        self.sub_odom = self.create_subscription(Odometry, TOPIC_ODOM,
                                                 self.odom_cb, 10)
        self.timer    = self.create_timer(1.0 / FREQ_HZ, self.loop)

        self.get_logger().info(
            f"Prueba {num_prueba} | ω={VEL_ANGULAR} rad/s | "
            f"t={DURACION:.2f} s | giro_teórico=360°")
        self.get_logger().info(f"Esperando primer mensaje de {TOPIC_ODOM}...")

    # ── callbacks ─────────────────────────────────────────────────────────────
    def odom_cb(self, msg: Odometry):
        o = msg.pose.pose.orientation
        yaw = quat_to_yaw(o.x, o.y, o.z, o.w)

        if self.fase == "esperar_odom":
            self._last_yaw = yaw

        elif self.fase == "girar":
            # Acumular rotación con manejo de wrap-around
            delta = normalize_angle(yaw - self.yaw_prev)
            self.yaw_acumulado += delta
            self.yaw_prev = yaw

        elif self.fase == "leer_final":
            self._yaw_final = yaw

    # ── loop principal ────────────────────────────────────────────────────────
    def loop(self):
        cmd = Twist()

        if self.fase == "esperar_odom":
            if not hasattr(self, "_last_yaw"):
                return
            self.get_logger().info(
                f"  /odom OK — yaw actual: {math.degrees(self._last_yaw):.2f}°")
            self.get_logger().info(
                f">>> ALINEA el robot con la marca de inicio. "
                f"Giro en {COUNTDOWN} s...")
            self.t_cuenta = time.time()
            self.fase = "countdown"

        elif self.fase == "countdown":
            restante = int(COUNTDOWN - (time.time() - self.t_cuenta))
            if restante != self.cuenta_ant and restante > 0:
                self.get_logger().info(f"  {restante}...")
                self.cuenta_ant = restante
            if time.time() - self.t_cuenta >= COUNTDOWN:
                self.yaw_inicial   = self._last_yaw
                self.yaw_prev      = self._last_yaw
                self.yaw_acumulado = 0.0
                self.t_inicio      = time.time()
                self.get_logger().info(
                    f"INICIO → yaw_inicial={math.degrees(self.yaw_inicial):.2f}°")
                self.fase = "girar"

        elif self.fase == "girar":
            elapsed = time.time() - self.t_inicio
            if elapsed < DURACION:
                cmd.angular.z = VEL_ANGULAR
                self.pub_cmd.publish(cmd)
                seg = int(elapsed)
                if seg != getattr(self, "_seg_ant", -1):
                    self.get_logger().info(
                        f"  t={elapsed:.1f}/{DURACION:.1f} s | "
                        f"acumulado={math.degrees(self.yaw_acumulado):.1f}°")
                    self._seg_ant = seg
            else:
                self.pub_cmd.publish(Twist())
                self.get_logger().info("Comando de parada enviado.")
                self.t_frenar = time.time()
                self.fase = "frenar"

        elif self.fase == "frenar":
            self.pub_cmd.publish(Twist())
            if time.time() - self.t_frenar >= SETTLE_TIME:
                self.get_logger().info("Leyendo orientación final...")
                self._yaw_final = self.yaw_prev   # valor ya actualizado por odom_cb
                self.fase = "leer_final"

        elif self.fase == "leer_final":
            if hasattr(self, "_yaw_final"):
                self._calcular_y_reportar()
                self.fase = "done"
                self.timer.cancel()
                # FIX: usar flag en vez de rclpy.shutdown() dentro de callback
                self._finished = True

    # ── reporte y log ──────────────────────────────────────────────────────────
    def _calcular_y_reportar(self):
        delta_odom_rad = self.yaw_acumulado
        delta_odom_deg = math.degrees(abs(delta_odom_rad))

        sep = "=" * 55
        self.get_logger().info(sep)
        self.get_logger().info(f"PRUEBA {self.num_prueba} — RESULTADOS")
        self.get_logger().info(sep)
        self.get_logger().info(
            f"  Yaw inicial (odom)  : {math.degrees(self.yaw_inicial):.2f}°")
        self.get_logger().info(
            f"  Yaw final   (odom)  : {math.degrees(self._yaw_final):.2f}°")
        self.get_logger().info(
            f"  Giro acumulado odom : {delta_odom_deg:.2f}°  (teórico: 360°)")
        self.get_logger().info(sep)
        self.get_logger().info(
            ">>> Mide AHORA el ángulo real con transportador y anótalo.")
        self.get_logger().info(
            "    Deriva = |ángulo_real - 360|")
        self.get_logger().info(sep)

        fname = os.path.join(SCRIPT_DIR, f"prueba_giro_{self.num_prueba}.log")
        with open(fname, "w") as f:
            f.write(f"prueba,{self.num_prueba}\n")
            f.write(f"giro_teorico_deg,360.0\n")
            f.write(f"delta_odom_deg,{delta_odom_deg:.6f}\n")
            f.write(f"yaw_inicial_deg,{math.degrees(self.yaw_inicial):.6f}\n")
            f.write(f"yaw_final_deg,{math.degrees(self._yaw_final):.6f}\n")
        self.get_logger().info(f"Log guardado: {fname}")


def main():
    parser = argparse.ArgumentParser(
        description="Prueba de giro completo 360° — odometría angular")
    parser.add_argument("--prueba", type=int, default=1,
                        help="Número de repetición (1-5)")
    args = parser.parse_args()

    rclpy.init()
    node = PruebaGiroNode(args.prueba)
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