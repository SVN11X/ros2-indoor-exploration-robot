import serial
import numpy as np
import time
import matplotlib.pyplot as plt
import os

# ==============================================================================
port     = 'COM4'
baudRate = 57600
ts       = 0.1
tf       = 10.0
PWM_STEP = 143
DATA_LAZO_ABIERTO = "step_response_velocity_lazo_abierto.npy"
# ==============================================================================

WHEEL_DIAMETER    = 0.067
ENC_TICKS_PER_REV = 1980
PID_RATE          = 30
TICKS_TO_MPS = (np.pi * WHEEL_DIAMETER * PID_RATE) / ENC_TICKS_PER_REV

def send_cmd(ser, cmd_str):
    """Envía un comando y espera la respuesta — completamente síncrono."""
    ser.write((cmd_str + '\r').encode())

def read_response(ser, timeout=0.05):
    """Lee una línea de respuesta del Arduino."""
    ser.timeout = timeout
    try:
        line = ser.readline().decode('utf-8').strip()
        return line
    except Exception:
        return ""

def read_encoders(ser):
    """Envía 'e' y parsea la respuesta 'enc_L enc_R'."""
    # Limpiar buffer pendiente
    ser.flushInput()
    send_cmd(ser, 'e')
    time.sleep(0.02)
    line = read_response(ser, timeout=0.05)
    parts = line.split()
    if len(parts) >= 2:
        try:
            return [int(parts[0]), int(parts[1])]
        except ValueError:
            pass
    return None  # señal de error

def set_pwm(ser, pwm_l, pwm_r):
    """Envía comando 'o' de PWM directo."""
    send_cmd(ser, f'o {int(pwm_l)} {int(pwm_r)}')
    # Leer y descartar el "OK" del firmware
    read_response(ser, timeout=0.02)

# ==============================================================================
print(f"Conectando a {port}...")
try:
    ser = serial.Serial(port, baudRate, timeout=1)
except Exception as e:
    print(f"ERROR: {e}")
    exit()

time.sleep(2)
print("Conectado.")

print(f"\n--- PRUEBA DE ESCALÓN EN LAZO ABIERTO ---")
print(f"PWM objetivo: {PWM_STEP}")
print(f"\nATENCIÓN: El robot se moverá SIN control PID.")
input("Presiona ENTER para comenzar...")

# Detener motores y verificar encoders
set_pwm(ser, 0, 0)
time.sleep(0.5)

# Test de comunicación
enc_test = read_encoders(ser)
if enc_test is None:
    print("ERROR: No se reciben datos del encoder. Verifica conexión serial.")
    ser.close()
    exit()
print(f"Encoders iniciales: L={enc_test[0]}  R={enc_test[1]}  ✓")

# Arrays de datos
t   = np.arange(0, tf + ts, ts)
N   = len(t)
cv  = np.zeros((N, 2))
pv  = np.zeros((N, 2))

enc_prev = enc_test

try:
    for k in range(N):
        start_time = time.time()

        # Escalón en t=1.0s
        pwm_send = PWM_STEP if t[k] >= 1.0 else 0
        cv[k] = [pwm_send, pwm_send]

        # 1. Enviar PWM
        set_pwm(ser, pwm_send, pwm_send)

        # 2. Leer encoders
        enc_now = read_encoders(ser)
        if enc_now is None:
            enc_now = enc_prev  # usar último valor válido
            print(f"  [WARN k={k}] Sin respuesta encoder, usando valor anterior")

        # 3. Calcular velocidad
        frames_per_sample   = ts * PID_RATE  # = 3 frames por muestra de 0.1s
        delta_izq = enc_now[0] - enc_prev[0]
        delta_der = enc_now[1] - enc_prev[1]

        pv[k, 0] = (delta_izq / frames_per_sample) * TICKS_TO_MPS
        pv[k, 1] = (delta_der / frames_per_sample) * TICKS_TO_MPS

        enc_prev = enc_now

        if k % 5 == 0:
            print(f"T={t[k]:.1f}s | PWM:{pwm_send:4d} | "
                  f"Enc: L={enc_now[0]:7d} R={enc_now[1]:7d} | "
                  f"Vel: L={pv[k,0]:.4f} R={pv[k,1]:.4f} m/s")

        # Control de tiempo
        elapsed    = time.time() - start_time
        sleep_time = ts - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

except KeyboardInterrupt:
    print("\nInterrupción por usuario.")

finally:
    print("\nDeteniendo motores...")
    set_pwm(ser, 0, 0)
    time.sleep(0.3)
    ser.close()
    print("Desconectado.")

    # Guardar
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path  = os.path.join(script_dir, DATA_LAZO_ABIERTO)
    with open(file_path, 'wb') as f:
        np.save(f, cv)
        np.save(f, pv)
        np.save(f, t)
        np.save(f, ts)
    print(f"Datos guardados en: {file_path}")

    # Diagnóstico
    idx_ss  = t >= 7.0
    vss_izq = np.mean(pv[idx_ss, 0])
    vss_der = np.mean(pv[idx_ss, 1])
    print(f"\nVelocidad estado estacionario (t > 7s):")
    print(f"  Izquierda: {vss_izq:.4f} m/s")
    print(f"  Derecha:   {vss_der:.4f} m/s")

    if vss_izq < 0.05 and vss_der < 0.05:
        print(f"  → Aún sin datos. Revisa que el Arduino responda al comando 'e'")
        print(f"    Prueba en el monitor serial de Arduino: escribe 'e' + Enter")
        print(f"    Deberías ver dos números separados por espacio.")
    elif vss_izq < 0.10:
        print(f"  → Sube PWM_STEP a {PWM_STEP + 20} y repite")
    elif vss_izq > 0.18:
        print(f"  → Baja PWM_STEP a {PWM_STEP - 15} y repite")
    else:
        print(f"  → Rango correcto ✓  Ejecuta SintonizacionAutomatica.py")

    # Gráfica
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    fig.suptitle(f"Respuesta al escalón LAZO ABIERTO (PWM={PWM_STEP})",
                 fontsize=13, fontweight='bold')
    ax1.plot(t, pv[:, 0], 'r', linewidth=1.5, label='Izquierda')
    ax1.axhline(0.13, color='k', linestyle='--', alpha=0.5, label='0.13 m/s')
    ax1.set_ylabel("Velocidad (m/s)"); ax1.set_title("Rueda izquierda")
    ax1.legend(); ax1.grid(True, alpha=0.3)

    ax2.plot(t, pv[:, 1], 'b', linewidth=1.5, label='Derecha')
    ax2.axhline(0.13, color='k', linestyle='--', alpha=0.5, label='0.13 m/s')
    ax2.set_xlabel("Tiempo (s)"); ax2.set_ylabel("Velocidad (m/s)")
    ax2.set_title("Rueda derecha"); ax2.legend(); ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    fig_path = os.path.join(script_dir, "respuesta_escalon_lazo_abierto.png")
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"Figura guardada en: {fig_path}")
    plt.show()