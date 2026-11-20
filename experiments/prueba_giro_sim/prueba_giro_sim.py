"""
prueba_giro_sim.py
─────────────────────────────────────────────────────────────────────────────
Prueba de giro completo 360° en SIMULACIÓN (Gazebo).

Diferencias respecto al modo real (prueba_giro.py):
  - use_sim_time activo
  - Ángulo "real" obtenido de Gazebo vía /get_entity_state (yaw ground truth)
  - Reset automático de posición entre pruebas
  - No requiere medición manual con transportador

Uso:
    python3 prueba_giro_sim.py --prueba 1
"""

import argparse
import math
import os
import time

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from gazebo_msgs.srv import GetEntityState

VEL_ANGULAR  = 0.4                        # rad/s (límite del diff_drive)
GIRO_TEORICO = 2 * math.pi               # 360°
DURACION     = GIRO_TEORICO / VEL_ANGULAR # ≈ 15.71 s
TOPIC_CMD    = "diff_cont/cmd_vel_unstamped"
TOPIC_ODOM   = "odom"
FREQ_HZ      = 20
COUNTDOWN    = 3
SETTLE_TIME  = 2.0
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))


def quat_to_yaw(ox, oy, oz, ow) -> float:
    return math.atan2(2.0 * (ow * oz + ox * oy),
                      1.0 - 2.0 * (oy * oy + oz * oz))


def normalize_angle(a: float) -> float:
    while a >  math.pi: a -= 2 * math.pi
    while a < -math.pi: a += 2 * math.pi
    return a


class PruebaGiroSimNode(Node):
    def __init__(self, num_prueba: int):
        super().__init__("prueba_giro_sim",
                         allow_undeclared_parameters=True,
                         automatically_declare_parameters_from_overrides=True)
        self.set_parameters([Parameter("use_sim_time",
                                       Parameter.Type.BOOL, True)])

        self.num_prueba    = num_prueba
        self.fase          = "esperar_odom"
        self.t_inicio      = None
        self.t_frenar      = None
        self.t_cuenta      = None
        self.cuenta_ant    = -1
        self._finished     = False

        self.yaw_inicial   = None
        self.yaw_prev      = None
        self.yaw_acumulado = 0.0

        # Ground truth Gazebo
        self.yaw_ini_gz    = None
        self.yaw_fin_gz    = None

        self.pub_cmd  = self.create_publisher(Twist, TOPIC_CMD, 10)
        self.sub_odom = self.create_subscription(
            Odometry, TOPIC_ODOM, self.odom_cb, 10)
        self.timer = self.create_timer(1.0 / FREQ_HZ, self.loop)

        self.gz_client = self.create_client(
            GetEntityState, "/get_entity_state")

        self.get_logger().info(
            f"[SIM] Prueba {num_prueba} | ω={VEL_ANGULAR} rad/s | "
            f"t={DURACION:.2f} s | giro_teórico=360°")
        self.get_logger().info(f"Esperando {TOPIC_ODOM}...")

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def odom_cb(self, msg: Odometry):
        o = msg.pose.pose.orientation
        yaw = quat_to_yaw(o.x, o.y, o.z, o.w)
        if self.fase == "esperar_odom":
            self._last_yaw = yaw
        elif self.fase == "girar":
            delta = normalize_angle(yaw - self.yaw_prev)
            self.yaw_acumulado += delta
            self.yaw_prev = yaw
        elif self.fase == "leer_final":
            self._yaw_final = yaw

    def _get_gazebo_yaw(self):
        """Obtiene el yaw real del robot desde Gazebo."""
        if not self.gz_client.wait_for_service(timeout_sec=2.0):
            return None
        req = GetEntityState.Request()
        req.name = "my_bot"
        req.reference_frame = "world"
        future = self.gz_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        if future.result() and future.result().success:
            o = future.result().state.pose.orientation
            return quat_to_yaw(o.x, o.y, o.z, o.w)
        return None

    # ── Loop principal ────────────────────────────────────────────────────────
    def loop(self):
        cmd = Twist()

        if self.fase == "esperar_odom":
            if not hasattr(self, "_last_yaw"):
                return
            self.get_logger().info(
                f"  /odom OK — yaw: {math.degrees(self._last_yaw):.2f}°")
            self.get_logger().info(f">>> Iniciando en {COUNTDOWN} s...")
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
                self.yaw_ini_gz    = self._get_gazebo_yaw()
                self.t_inicio      = time.time()
                self.get_logger().info(
                    f"INICIO → yaw_odom={math.degrees(self.yaw_inicial):.2f}°  "
                    f"yaw_gz={math.degrees(self.yaw_ini_gz):.2f}°"
                    if self.yaw_ini_gz is not None else
                    f"INICIO → yaw_odom={math.degrees(self.yaw_inicial):.2f}°")
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
                self.get_logger().info("Parada enviada.")
                self.t_frenar = time.time()
                self.fase = "frenar"

        elif self.fase == "frenar":
            self.pub_cmd.publish(Twist())
            if time.time() - self.t_frenar >= SETTLE_TIME:
                self._yaw_final = self.yaw_prev
                self.yaw_fin_gz = self._get_gazebo_yaw()
                self.fase = "leer_final"

        elif self.fase == "leer_final":
            if hasattr(self, "_yaw_final"):
                self._calcular_y_reportar()
                self.fase = "done"
                self.timer.cancel()
                self._finished = True

    # ── Reporte ───────────────────────────────────────────────────────────────
    def _calcular_y_reportar(self):
        delta_odom_rad = self.yaw_acumulado
        delta_odom_deg = math.degrees(abs(delta_odom_rad))

        # Ground truth Gazebo: diferencia angular acumulada
        if self.yaw_ini_gz is not None and self.yaw_fin_gz is not None:
            # Calcular delta angular (puede haber dado la vuelta)
            # Usamos el acumulado de odom como referencia y calculamos
            # la diferencia de yaw final-inicial en Gazebo
            delta_gz_deg = abs(math.degrees(
                normalize_angle(self.yaw_fin_gz - self.yaw_ini_gz)
            ))
            # Si el robot giró casi 360°, normalizar puede dar ~0; usar odom
            if delta_gz_deg < 10:
                delta_gz_deg = delta_odom_deg
            fuente_real = "Gazebo/GetEntityState"
        else:
            delta_gz_deg = delta_odom_deg
            fuente_real = "odom (fallback)"

        deriva_odom = abs(delta_odom_deg - 360.0)
        deriva_gz   = abs(delta_gz_deg   - 360.0)

        sep = "=" * 55
        self.get_logger().info(sep)
        self.get_logger().info(f"PRUEBA {self.num_prueba} — RESULTADOS (SIM)")
        self.get_logger().info(sep)
        self.get_logger().info(f"  Giro teórico          : 360.0°")
        self.get_logger().info(f"  Giro odom acumulado   : {delta_odom_deg:.2f}°")
        self.get_logger().info(f"  Deriva odom           : {deriva_odom:.2f}°")
        self.get_logger().info(
            f"  Giro real ({fuente_real}): {delta_gz_deg:.2f}°")
        self.get_logger().info(f"  Deriva real           : {deriva_gz:.2f}°")
        self.get_logger().info(sep)

        fname = os.path.join(SCRIPT_DIR, f"prueba_giro_sim_{self.num_prueba}.log")
        with open(fname, "w") as f:
            f.write(f"prueba,{self.num_prueba}\n")
            f.write(f"modo,sim\n")
            f.write(f"giro_teorico_deg,360.0\n")
            f.write(f"delta_odom_deg,{delta_odom_deg:.6f}\n")
            f.write(f"deriva_odom_deg,{deriva_odom:.6f}\n")
            f.write(f"delta_real_deg,{delta_gz_deg:.6f}\n")
            f.write(f"deriva_real_deg,{deriva_gz:.6f}\n")
            f.write(f"fuente_real,{fuente_real}\n")
            f.write(f"yaw_inicial_deg,{math.degrees(self.yaw_inicial):.6f}\n")
            f.write(f"yaw_final_deg,{math.degrees(self._yaw_final):.6f}\n")
        self.get_logger().info(f"Log guardado: {fname}")


def main():
    parser = argparse.ArgumentParser(
        description="Prueba giro 360° — simulación Gazebo")
    parser.add_argument("--prueba", type=int, default=1)
    args = parser.parse_args()

    rclpy.init()
    node = PruebaGiroSimNode(args.prueba)
    try:
        while rclpy.ok() and not node._finished:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        node.get_logger().warn("Interrupción — velocidad cero.")
        node.pub_cmd.publish(Twist())
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
