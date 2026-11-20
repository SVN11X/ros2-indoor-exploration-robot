#!/usr/bin/env python3
"""
RPLidar A1 publisher (Python, serial nativo) para ROS 2 Foxy.

Inspirado en sllidar_ros2 (Slamtec, C++). 
- Reset + drain al arrancar (estado conocido, independiente de sesión previa).
- get_info y get_health al inicio: aborta si el lidar está en ERROR.
- scan_time medido entre publishes (no hardcoded).
- intensities desde el campo quality del paquete (no array de ceros).
- Servicios stop_scan / start_scan para tests sin matar el nodo.
- Cierre limpio: STOP + close serial.
- Detección de fin de revolución por wrap angular (no por bit S).
- Binning angular fijo de 360 bins → angle_min/max/increment constantes.
- Validación S/S̄/C por paquete + resync defensivo.
"""

import serial
import struct
import math
import time
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from std_srvs.srv import Empty


# Comandos del protocolo RPLidar A1
CMD_STOP        = 0x25
CMD_RESET       = 0x40
CMD_SCAN        = 0x20
CMD_GET_INFO    = 0x50
CMD_GET_HEALTH  = 0x52

# Tipos de respuesta esperados
RESP_TYPE_INFO   = 0x04
RESP_TYPE_HEALTH = 0x06
RESP_TYPE_SCAN   = 0x81

# Estados de salud
HEALTH_OK      = 0
HEALTH_WARNING = 1
HEALTH_ERROR   = 2


class RPLidarPublisher(Node):
    def __init__(self):
        super().__init__('rplidar_serial_publisher')

        # --- Parámetros ROS ---
        self.declare_parameter('port', '/dev/rlidar_gpio')
        self.declare_parameter('baudrate', 115200)
        self.declare_parameter('frame_id', 'laser_frame')
        self.declare_parameter('range_min', 0.15)
        self.declare_parameter('range_max', 12.0)
        self.declare_parameter('angular_bins', 230)
        self.declare_parameter('min_points_per_scan', 100)
        self.declare_parameter('min_points_per_revolution', 180)
        self.declare_parameter('invert_angle', True)

        self.port            = self.get_parameter('port').value
        self.baudrate        = self.get_parameter('baudrate').value
        self.frame_id        = self.get_parameter('frame_id').value
        self.range_min       = self.get_parameter('range_min').value
        self.range_max       = self.get_parameter('range_max').value
        self.angular_bins    = int(self.get_parameter('angular_bins').value)
        self.min_pts         = int(self.get_parameter('min_points_per_scan').value)
        self.min_pts_rev     = int(self.get_parameter('min_points_per_revolution').value)
        self.invert_angle    = bool(self.get_parameter('invert_angle').value)

        # --- Conexión serial ---
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
        except serial.SerialException as e:
            self.get_logger().fatal(f'No se pudo abrir {self.port}: {e}')
            raise

        self.get_logger().info(f'Serial abierto en {self.port} @ {self.baudrate}')

        # --- Estado del lidar ---
        self._reset_lidar()

        info = self._get_info()
        if info:
            self.get_logger().info(
                f'RPLidar — Modelo: 0x{info["model"]:02X}  '
                f'FW: {info["fw_major"]}.{info["fw_minor"]:02d}  '
                f'HW: {info["hw"]}  '
                f'S/N: {info["serial"]}'
            )
        else:
            self.get_logger().warn('No se pudo obtener device info (no fatal)')

        health = self._get_health()
        if health is None:
            self.get_logger().fatal('No se pudo leer health del lidar — abortando')
            raise RuntimeError('Health check failed')

        if health['status'] == HEALTH_ERROR:
            self.get_logger().fatal(
                f'Lidar en ERROR (code 0x{health["error_code"]:04X}). '
                f'Desenchufar y reconectar.'
            )
            raise RuntimeError('Lidar in error state')
        elif health['status'] == HEALTH_WARNING:
            self.get_logger().warn(
                f'Lidar en WARNING (code 0x{health["error_code"]:04X}) — continúo'
            )
        else:
            self.get_logger().info('Health: OK')

        # --- Publisher ROS ---
        self.pub = self.create_publisher(LaserScan, 'scan', qos_profile_sensor_data)

        # --- Servicios para tests ---
        self.srv_stop  = self.create_service(Empty, '~/stop_scan',  self._srv_stop_scan)
        self.srv_start = self.create_service(Empty, '~/start_scan', self._srv_start_scan)

        # --- Iniciar scan ---
        self._start_scan()

        # --- Estado del parser ---
        self.buffer = b''
        self.nodes = []                       # (angle_q6, dist_q2, quality)
        self.synced = False
        self.bad_packet_count = 0
        self.last_publish_time = self.get_clock().now()
        self.scan_time = 0.18                 # default razonable hasta medir

        self.timer = self.create_timer(0.05, self.timer_callback)

    # ------------------------------------------------------------
    # Comandos del protocolo
    # ------------------------------------------------------------

    def _send_cmd(self, cmd_byte: int):
        self.ser.write(bytes([0xA5, cmd_byte]))
        self.ser.flush()

    def _wait_response_header(self, timeout: float = 1.0):
        """Lee descriptor de respuesta: 7 bytes (0xA5 0x5A + len30 + mode2 + type)."""
        deadline = time.time() + timeout
        header = b''
        while len(header) < 7:
            remaining = deadline - time.time()
            if remaining <= 0:
                return None
            self.ser.timeout = remaining
            chunk = self.ser.read(7 - len(header))
            if not chunk:
                return None
            header += chunk

        if header[0] != 0xA5 or header[1] != 0x5A:
            self.get_logger().warn(f'Header inválido: {header.hex()}')
            return None

        size_word = struct.unpack('<I', header[2:6])[0]
        length    = size_word & 0x3FFFFFFF
        send_mode = (size_word >> 30) & 0x3
        data_type = header[6]
        return {'length': length, 'send_mode': send_mode, 'type': data_type}

    def _reset_lidar(self):
        """STOP + RESET + drain. Deja el lidar en estado conocido."""
        try:
            self._send_cmd(CMD_STOP)
            time.sleep(0.1)
            self._send_cmd(CMD_RESET)
            time.sleep(1.0)                 # El A1 tarda en reiniciar
            self.ser.reset_input_buffer()   # descarta banner de boot
            time.sleep(0.2)
            self.ser.reset_input_buffer()
        except Exception as e:
            self.get_logger().warn(f'reset_lidar: {e}')

    def _get_info(self):
        try:
            self.ser.reset_input_buffer()
            self._send_cmd(CMD_GET_INFO)
            hdr = self._wait_response_header()
            if not hdr or hdr['type'] != RESP_TYPE_INFO or hdr['length'] != 20:
                return None
            payload = self.ser.read(20)
            if len(payload) != 20:
                return None
            return {
                'model':     payload[0],
                'fw_minor':  payload[1],
                'fw_major':  payload[2],
                'hw':        payload[3],
                'serial':    payload[4:20].hex().upper(),
            }
        except Exception as e:
            self.get_logger().warn(f'get_info: {e}')
            return None

    def _get_health(self):
        try:
            self.ser.reset_input_buffer()
            self._send_cmd(CMD_GET_HEALTH)
            hdr = self._wait_response_header()
            if not hdr or hdr['type'] != RESP_TYPE_HEALTH or hdr['length'] != 3:
                return None
            payload = self.ser.read(3)
            if len(payload) != 3:
                return None
            status     = payload[0]
            error_code = struct.unpack('<H', payload[1:3])[0]
            return {'status': status, 'error_code': error_code}
        except Exception as e:
            self.get_logger().warn(f'get_health: {e}')
            return None

    def _start_scan(self):
        self.ser.reset_input_buffer()
        self._send_cmd(CMD_SCAN)
        hdr = self._wait_response_header(timeout=1.0)
        if not hdr:
            raise RuntimeError('Sin respuesta a START_SCAN')
        if hdr['type'] != RESP_TYPE_SCAN:
            raise RuntimeError(f'Tipo de respuesta scan inesperado: 0x{hdr["type"]:02X}')
        self.get_logger().info('Scan iniciado, streaming activo')

    # ------------------------------------------------------------
    # Servicios ROS
    # ------------------------------------------------------------

    def _srv_stop_scan(self, req, res):
        self._send_cmd(CMD_STOP)
        self.get_logger().info('Scan detenido por servicio')
        return res

    def _srv_start_scan(self, req, res):
        try:
            self._start_scan()
            self.synced = False
            self.nodes = []
            self.buffer = b''
        except Exception as e:
            self.get_logger().error(f'No se pudo reiniciar scan: {e}')
        return res

    # ------------------------------------------------------------
    # Helpers de validación de paquetes scan
    # ------------------------------------------------------------

    def _valid_node(self, buf, i):
        """S != S̄ y check-bit del ángulo = 1."""
        if i + 4 >= len(buf):
            return False
        b0 = buf[i]
        s     = b0 & 0x01
        s_inv = (b0 >> 1) & 0x01
        if s == s_inv:
            return False
        if not (buf[i + 1] & 0x01):
            return False
        return True

    def _is_revolution_start(self, buf, i):
        """Nodo válido + S=1 + ángulo bajo (sync inicial)."""
        if not self._valid_node(buf, i):
            return False
        if not (buf[i] & 0x01):
            return False
        raw_angle = struct.unpack_from('<H', buf, i + 1)[0]
        angle_q6 = raw_angle >> 1
        return angle_q6 <= 1000

    # ------------------------------------------------------------
    # Loop principal de parseo
    # ------------------------------------------------------------

    def timer_callback(self):
        if self.ser.in_waiting > 0:
            self.buffer += self.ser.read(self.ser.in_waiting)

        # Sincronización inicial
        if not self.synced:
            pos = -1
            for i in range(max(0, len(self.buffer) - 4)):
                if self._is_revolution_start(self.buffer, i):
                    pos = i
                    break
            if pos == -1:
                if len(self.buffer) > 4:
                    self.buffer = self.buffer[-4:]
                return
            self.buffer = self.buffer[pos:]
            self.synced = True
            self.get_logger().info('Sincronizado al inicio de revolución')

        # Procesar paquetes de 5 bytes
        while len(self.buffer) >= 5:
            if not self._valid_node(self.buffer, 0):
                self.buffer = self.buffer[1:]
                self.bad_packet_count += 1
                if self.bad_packet_count > 20:
                    self.get_logger().warn('Demasiados paquetes inválidos, resync')
                    self.synced = False
                    self.nodes = []
                    self.bad_packet_count = 0
                    return
                continue

            self.bad_packet_count = 0
            raw = self.buffer[:5]
            quality   = (raw[0] >> 2) & 0x3F
            raw_angle = struct.unpack_from('<H', raw, 1)[0]
            angle_q6  = raw_angle >> 1
            dist_q2   = struct.unpack_from('<H', raw, 3)[0]
            self.buffer = self.buffer[5:]

            # Fin de revolución por wrap angular (>187° de retroceso)
            if self.nodes:
                last_angle = self.nodes[-1][0]
                if last_angle - angle_q6 > 12000:
                    if len(self.nodes) >= self.min_pts_rev:
                        # Wrap legítimo: publicar y empezar nueva revolución
                        self.publish_scan(self.nodes)
                        self.nodes = []
                    else:
                        # Wrap "temprano": el paquete actual tiene ángulo
                        # corrupto pero pasó la validación S/S̄/C por azar.
                        # Lo descartamos sin tocar self.nodes para no
                        # fragmentar la revolución en curso.
                        continue

            self.nodes.append((angle_q6, dist_q2, quality))

    # ------------------------------------------------------------
    # Publicación
    # ------------------------------------------------------------

    def publish_scan(self, nodes):
        if len(nodes) < self.min_pts:
            self.get_logger().debug(f'Revolución descartada: {len(nodes)} pts')
            return

        now = self.get_clock().now()

        # scan_time medido con clamp por sanidad
        delta = (now - self.last_publish_time).nanoseconds * 1e-9
        if 0.05 < delta < 2.0:
            self.scan_time = delta
        self.last_publish_time = now

        N = self.angular_bins
        angle_increment = 2.0 * math.pi / N
        ranges      = [float('inf')] * N
        intensities = [0.0] * N

        for a_q6, d_q2, q in nodes:
            ang  = (a_q6 / 64.0) * (math.pi / 180.0)
            ang  = ang % (2.0 * math.pi)
            if self.invert_angle:                        # ← AGREGAR
                ang = (2.0 * math.pi - ang) % (2.0 * math.pi)   # ← AGREGAR
            dist = d_q2 / 4000.0 if d_q2 > 0 else float('inf')
            if dist < self.range_min or dist > self.range_max:
                dist = float('inf')
            bin_idx = int(ang / angle_increment) % N
            if dist < ranges[bin_idx]:
                ranges[bin_idx]      = dist
                intensities[bin_idx] = float(q)

        msg = LaserScan()
        msg.header.stamp    = now.to_msg()
        msg.header.frame_id = self.frame_id
        msg.angle_min       = 0.0
        msg.angle_max       = 2.0 * math.pi - angle_increment
        msg.angle_increment = angle_increment
        msg.scan_time       = self.scan_time
        msg.time_increment  = self.scan_time / N
        msg.range_min       = self.range_min
        msg.range_max       = self.range_max
        msg.ranges          = ranges
        msg.intensities     = intensities

        self.pub.publish(msg)

    # ------------------------------------------------------------
    # Cierre limpio
    # ------------------------------------------------------------

    def destroy_node(self):
        try:
            self._send_cmd(CMD_STOP)
            time.sleep(0.05)
            self.ser.close()
            self.get_logger().info('Lidar detenido y serial cerrado')
        except Exception:
            pass
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    try:
        node = RPLidarPublisher()
    except Exception as e:
        # rclpy ya está inicializado; loguear y salir limpio
        rclpy.logging.get_logger('rplidar_serial_publisher').fatal(str(e))
        rclpy.shutdown()
        return
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()