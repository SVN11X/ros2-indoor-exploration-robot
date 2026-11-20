"""
prueba_recta_sim.py
─────────────────────────────────────────────────────────────────────────────
Prueba de trayectoria rectilínea en SIMULACIÓN (Gazebo).

Diferencias respecto al modo real (prueba_recta.py):
  - use_sim_time: el nodo usa el reloj de Gazebo (/clock)
  - Distancia "real": se obtiene de Gazebo vía /get_entity_state
    (ground truth exacto, sin cinta métrica)
  - No requiere interacción manual entre pruebas

Uso:
    python3 prueba_recta_sim.py --prueba 1
"""

import argparse
import math
import time
import os

import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from gazebo_msgs.srv import GetEntityState

VEL_LINEAL   = 0.13          # m/s (límite del diff_drive_controller)
DIST_TEORICA = 2.00           # m
DURACION     = DIST_TEORICA / VEL_LINEAL
TOPIC_CMD    = "diff_cont/cmd_vel_unstamped"
TOPIC_ODOM   = "odom"
FREQ_HZ      = 20
COUNTDOWN    = 3              # segundos antes de arrancar (menor que en real)
SETTLE_TIME  = 2.0
SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))


class PruebaRectaSimNode(Node):
    def __init__(self, num_prueba: int):
        super().__init__("prueba_recta_sim",
                         allow_undeclared_parameters=True,
                         automatically_declare_parameters_from_overrides=True)
        # Activar use_sim_time
        self.set_parameters([Parameter("use_sim_time",
                                       Parameter.Type.BOOL, True)])

        self.num_prueba = num_prueba
        self.xi = self.yi = None
        self.xf = self.yf = None
        self.xi_gz = self.yi_gz = None   # ground truth Gazebo al inicio
        self.xf_gz = self.yf_gz = None   # ground truth Gazebo al final
        self.fase = "esperar_odom"
        self._finished = False
        self.t_inicio = None
        self.t_frenar = None
        self.t_cuenta = None
        self.cuenta_ant = -1

        self.pub_cmd  = self.create_publisher(Twist, TOPIC_CMD, 10)
        self.sub_odom = self.create_subscription(
            Odometry, TOPIC_ODOM, self.odom_cb, 10)
        self.timer = self.create_timer(1.0 / FREQ_HZ, self.loop)

        # Cliente Gazebo para ground truth
        self.gz_client = self.create_client(
            GetEntityState, "/get_entity_state")

        self.get_logger().info(
            f"[SIM] Prueba {num_prueba} | v={VEL_LINEAL} m/s | "
            f"t={DURACION:.2f} s | dist_teórica={DIST_TEORICA} m")
        self.get_logger().info(
            f"Esperando primer mensaje de {TOPIC_ODOM}...")

    # ── Callbacks ────────────────────────────────────────────────────────────
    def odom_cb(self, msg: Odometry):
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        if self.fase == "esperar_odom":
            self._last_x, self._last_y = x, y
        elif self.fase == "leer_final":
            self.xf, self.yf = x, y

    def _get_gazebo_pose(self):
        """Consulta la posición real del robot en Gazebo (ground truth)."""
        if not self.gz_client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warn(
                "Servicio /get_entity_state no disponible — "
                "usando odom como ground truth.")
            return None, None
        req = GetEntityState.Request()
        req.name = "my_bot"
        req.reference_frame = "world"
        future = self.gz_client.call_async(req)
        rclpy.spin_until_future_complete(self, future, timeout_sec=3.0)
        if future.result() and future.result().success:
            p = future.result().state.pose.position
            return p.x, p.y
        return None, None

    # ── Loop principal ───────────────────────────────────────────────────────
    def loop(self):
        cmd = Twist()

        if self.fase == "esperar_odom":
            if not hasattr(self, "_last_x"):
                return
            self.get_logger().info(
                f"  /odom OK — posición: x={self._last_x:.4f} y={self._last_y:.4f}")
            self.get_logger().info(
                f">>> Iniciando en {COUNTDOWN} s...")
            self.t_cuenta = time.time()
            self.fase = "countdown"

        elif self.fase == "countdown":
            restante = int(COUNTDOWN - (time.time() - self.t_cuenta))
            if restante != self.cuenta_ant and restante > 0:
                self.get_logger().info(f"  {restante}...")
                self.cuenta_ant = restante
            if time.time() - self.t_cuenta >= COUNTDOWN:
                self.xi, self.yi = self._last_x, self._last_y
                self.xi_gz, self.yi_gz = self._get_gazebo_pose()
                self.get_logger().info(
                    f"INICIO odom → xi={self.xi:.4f} yi={self.yi:.4f}")
                if self.xi_gz is not None:
                    self.get_logger().info(
                        f"INICIO gt   → xi={self.xi_gz:.4f} yi={self.yi_gz:.4f}")
                self.t_inicio = time.time()
                self.fase = "mover"

        elif self.fase == "mover":
            elapsed = time.time() - self.t_inicio
            if elapsed < DURACION:
                cmd.linear.x = VEL_LINEAL
                self.pub_cmd.publish(cmd)
                seg = int(elapsed)
                if seg != getattr(self, "_seg_ant", -1):
                    self.get_logger().info(
                        f"  t={elapsed:.1f}/{DURACION:.1f} s")
                    self._seg_ant = seg
            else:
                self.pub_cmd.publish(Twist())
                self.get_logger().info("Comando de parada enviado.")
                self.t_frenar = time.time()
                self.fase = "frenar"

        elif self.fase == "frenar":
            self.pub_cmd.publish(Twist())
            if time.time() - self.t_frenar >= SETTLE_TIME:
                self.get_logger().info("Leyendo posición final...")
                self.fase = "leer_final"

        elif self.fase == "leer_final":
            if self.xf is not None:
                self.xf_gz, self.yf_gz = self._get_gazebo_pose()
                self._calcular_y_reportar()
                self.fase = "done"
                self.timer.cancel()
                self._finished = True

    # ── Reporte ──────────────────────────────────────────────────────────────
    def _calcular_y_reportar(self):
        dist_odom = math.sqrt((self.xf - self.xi)**2 + (self.yf - self.yi)**2)

        # Ground truth: posición real de Gazebo
        if self.xi_gz is not None and self.xf_gz is not None:
            dist_real = math.sqrt(
                (self.xf_gz - self.xi_gz)**2 + (self.yf_gz - self.yi_gz)**2)
            fuente_real = "Gazebo/GetEntityState"
        else:
            # Fallback: en sim ideal, odom ≈ real
            dist_real = dist_odom
            fuente_real = "odom (fallback, /get_entity_state no disponible)"

        error_pct = abs(dist_odom - dist_real) / dist_real * 100 \
            if dist_real > 0 else 0.0

        sep = "=" * 55
        self.get_logger().info(sep)
        self.get_logger().info(f"PRUEBA {self.num_prueba} — RESULTADOS (SIM)")
        self.get_logger().info(sep)
        self.get_logger().info(
            f"  Pos. inicial odom : x={self.xi:.4f}  y={self.yi:.4f} m")
        self.get_logger().info(
            f"  Pos. final   odom : x={self.xf:.4f}  y={self.yf:.4f} m")
        self.get_logger().info(
            f"  Dist. teórica     : {DIST_TEORICA:.3f} m")
        self.get_logger().info(
            f"  Dist. odom        : {dist_odom:.4f} m")
        self.get_logger().info(
            f"  Dist. real ({fuente_real}): {dist_real:.4f} m")
        self.get_logger().info(
            f"  Error (%)         : {error_pct:.2f}%")
        self.get_logger().info(sep)

        # Guardar log
        fname = os.path.join(SCRIPT_DIR, f"prueba_recta_sim_{self.num_prueba}.log")
        with open(fname, "w") as f:
            f.write(f"prueba,{self.num_prueba}\n")
            f.write(f"modo,sim\n")
            f.write(f"dist_teorica,{DIST_TEORICA:.4f}\n")
            f.write(f"dist_odom,{dist_odom:.6f}\n")
            f.write(f"dist_real,{dist_real:.6f}\n")
            f.write(f"fuente_real,{fuente_real}\n")
            f.write(f"error_pct,{error_pct:.4f}\n")
            f.write(f"xi,{self.xi:.6f}\n")
            f.write(f"yi,{self.yi:.6f}\n")
            f.write(f"xf,{self.xf:.6f}\n")
            f.write(f"yf,{self.yf:.6f}\n")
            if self.xi_gz is not None:
                f.write(f"xi_gz,{self.xi_gz:.6f}\n")
                f.write(f"yi_gz,{self.yi_gz:.6f}\n")
                f.write(f"xf_gz,{self.xf_gz:.6f}\n")
                f.write(f"yf_gz,{self.yf_gz:.6f}\n")
        self.get_logger().info(f"Log guardado: {fname}")


def main():
    parser = argparse.ArgumentParser(
        description="Prueba de trayectoria rectilínea — simulación Gazebo")
    parser.add_argument("--prueba", type=int, default=1,
                        help="Número de repetición (1-5)")
    args = parser.parse_args()

    rclpy.init()
    node = PruebaRectaSimNode(args.prueba)
    try:
        while rclpy.ok() and not node._finished:
            rclpy.spin_once(node, timeout_sec=0.1)
    except KeyboardInterrupt:
        node.get_logger().warn("Interrupción — enviando velocidad cero.")
        node.pub_cmd.publish(Twist())
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == "__main__":
    main()
