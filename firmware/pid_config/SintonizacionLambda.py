#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SintonizacionLambda.py
======================
Calcula las ganancias PID mediante sintonía Lambda a partir de los
parámetros FODT identificados por PSO, y compara la respuesta simulada
en lazo cerrado con las ganancias PSO vs. Lambda.

Ubicación esperada: firmware/pid_config/SintonizacionLambda.py
Prerrequisitos:
  - Haber ejecutado ControlLazoAbierto.py  (genera step_response_velocity_lazo_abierto.npy)
  - Haber ejecutado SintonizacionAutomatica.py (para conocer los parámetros FODT)

Uso:
  python SintonizacionLambda.py

Referencia teórica: Sección "Sintonía Lambda" del marco teórico de la tesis.
"""

from pyPso import *
from scipy.ndimage import uniform_filter1d
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
import json

# =============================================================================
# Constantes — idénticas a SintonizacionAutomatica.py
# =============================================================================
SCALE_MODEL = np.array([0.01, 2.0, 0.5])   # [K en m/s/PWM, Tau s, Delay s]
ARDUINO_KO  = 50.0
MAX_PWM     = 255.0

# PWM que produce ~0.13 m/s en estado estacionario (medido en ControlLazoAbierto.py)
PWM_NOMINAL = 143.0

# Factor Lambda: λ = LAMBDA_FACTOR * τ
# λ = 3τ → sintonía robusta (recomendada)
LAMBDA_FACTOR = 3.0

# Constantes físicas del robot
WHEEL_DIAMETER    = 0.067
ENC_TICKS_PER_REV = 1980
PID_RATE          = 30
MPS_TO_TICKS = ENC_TICKS_PER_REV / (np.pi * WHEEL_DIAMETER * PID_RATE)  # 313.56

# Archivo de datos de lazo abierto
DATA_FILE = "step_response_velocity_lazo_abierto.npy"

# =============================================================================
# Función FODT
# =============================================================================
def fodt(cv, t, ts, params):
    """Simula un modelo FODT en tiempo discreto. Entrada: PWM, salida: m/s."""
    km, tau, delay = params
    N = len(t)
    pv_est = np.zeros(N)
    if tau < 0.001:
        tau = 0.001
    for k in range(1, N):
        dt = float(ts[k]) if hasattr(ts, '__len__') and len(ts) > 1 else float(ts)
        steps_back = int(delay / dt) if dt > 0 else 0
        idx_delay  = max(k - steps_back, 0)
        u_delayed  = cv[idx_delay]
        pv_est[k]  = pv_est[k-1] + (dt / tau) * (km * u_delayed - pv_est[k-1])
    return pv_est


def costFunction_ID(x):
    """Función de costo para identificación FODT (MSE sobre datos suavizados)."""
    cost = np.zeros(x.shape[0])
    for i in range(x.shape[0]):
        params_real = x[i] * SCALE_MODEL
        if params_real[1] < 0.01:
            cost[i] = 1e6
            continue
        pve = fodt(g_cv, g_t, g_ts, params_real)
        if np.any(np.isnan(pve)) or np.any(np.isinf(pve)):
            cost[i] = 1e6
            continue
        cost[i] = np.mean((g_pv_smooth - pve) ** 2)
    return cost


# =============================================================================
# Simulación PID — réplica exacta del firmware doPID()
# Usada para AMBOS métodos (PSO y Lambda) garantizando comparación justa.
# =============================================================================
def simular_pid_firmware(pid_params, model_params, cv_signal_mps, t, ts_val, deadband=0):
    """
    Réplica del firmware ROSArduinoBridge:
      - PID incremental
      - Derivada sobre la medición (evita derivative kick)
      - Divisor Ko
      - Anti-windup condicional
      - Deadband configurable

    pid_params    : [Kp_fw, Kd_fw, Ki_fw]  — ganancias en formato firmware
    model_params  : [km, tau, delay]        — km en m/s/PWM (lazo abierto)
    cv_signal_mps : setpoint en m/s
    """
    kp, kd, ki   = pid_params
    km, tau, delay = model_params

    t_sim = np.arange(t[0], t[-1] + ts_val, ts_val)
    N     = len(t_sim)

    pv_sim     = np.zeros(N)
    output     = 0.0
    ITerm      = 0.0
    prev_input = 0

    if tau < 1e-4:
        tau = 1e-4
    delay_steps = int(delay / ts_val)

    for k in range(1, N):
        # Interpolar setpoint al timestep del firmware
        setpoint_k = float(np.interp(t_sim[k], t, cv_signal_mps))

        # Planta FODT: entrada PWM → salida m/s
        pv_sim[k] = pv_sim[k-1] + (ts_val / tau) * (km * output - pv_sim[k-1])
        pv_sim[k] = max(0.0, pv_sim[k])

        # Convertir a ticks (igual que el firmware)
        target_ticks  = setpoint_k * MPS_TO_TICKS
        current_input = int(round(pv_sim[k] * MPS_TO_TICKS))
        Perror        = target_ticks - current_input

        # Deadband
        if abs(Perror) <= deadband:
            Perror = 0

        # PID incremental — réplica de doPID()
        delta_u = (kp * Perror - kd * (current_input - prev_input) + ITerm) / ARDUINO_KO
        output += delta_u

        # Saturación y anti-windup condicional
        if output >= MAX_PWM:
            output = MAX_PWM
        elif output <= -MAX_PWM:
            output = -MAX_PWM
        else:
            ITerm += ki * Perror
            # NOTA: Este clipping adicional del integrador NO existe en el firmware
            # real (diff_controller.h) ni en SintonizacionAutomatica.py.
            # Se mantiene como protección conservadora de la simulación Lambda.
            # Véase la nota de simplificaciones en la sección de sintonización del texto.
            ITerm = np.clip(ITerm, -MAX_PWM * ARDUINO_KO, MAX_PWM * ARDUINO_KO)

        prev_input = current_input

    return np.interp(t, t_sim, pv_sim)


# =============================================================================
# Conversión de ganancias Lambda → formato firmware
#
# Lambda produce ganancias en forma estándar [m/s → señal normalizada 0-1].
# El firmware trabaja en [ticks/frame → PWM], dividiendo por Ko.
#
# Conversión:
#   Kp_fw = Kp_std × PWM_NOMINAL × Ko / MPS_TO_TICKS
#   (análoga para Kd y Ki)
#
# Verificación dimensional:
#   Kp_std × error[m/s] = señal normalizada
#   señal normalizada × PWM_NOMINAL = PWM
#   Kp_fw × error[ticks] / Ko = PWM
#   → Kp_fw = Kp_std × PWM_NOMINAL × Ko / MPS_TO_TICKS
# =============================================================================
def lambda_a_firmware(kp_std, kd_std, ki_std):
    """Convierte ganancias Lambda (forma estándar) al formato del firmware."""
    factor    = PWM_NOMINAL * ARDUINO_KO / MPS_TO_TICKS
    ts_pid    = 1.0 / PID_RATE   # 0.0333s — factor de discretización para Ki
    kp_fw = kp_std * factor
    kd_fw = kd_std * factor
    ki_fw = ki_std * factor * ts_pid   # ← agregar ts_pid solo a Ki
    return kp_fw, kd_fw, ki_fw


# =============================================================================
# Cálculo de ganancias Lambda (IMC)
# =============================================================================
def calcular_ganancias_lambda(km_norm, tau, delay, lambda_factor=3.0):
    """
    Calcula ganancias PID usando sintonía Lambda (IMC) para un modelo FODT.

    Recibe km_norm = km_original × PWM_NOMINAL (≈ 0.13), que normaliza la
    ganancia estática al rango de velocidad operativa del robot.

    Paso 1 — Forma serie (interactuante):
        kc' = τ / (K_norm · (L/2 + λ))
        ti' = τ
        td' = L / 2

    Paso 2 — Conversión a forma paralela estándar:
        kp = kc' · (ti' + td') / ti'
        ti = ti' + td'
        td = (ti' · td') / (ti' + td')

    Paso 3 — Ganancias PID estándar:
        Kp_std = kp
        Ki_std = kp / ti
        Kd_std = kp · td
    """
    L   = delay
    lam = lambda_factor * tau   # λ = factor × τ

    # Protección contra valores degenerados
    km_norm = max(km_norm, 1e-6)
    tau     = max(tau,     1e-4)
    L       = max(L,       1e-6)

    # Paso 1 — Forma serie
    kc_prime = tau / (km_norm * (L / 2.0 + lam))
    ti_prime = tau
    td_prime = L / 2.0

    # Paso 2 — Forma paralela
    kp_std = kc_prime * (ti_prime + td_prime) / ti_prime
    ti_std = ti_prime + td_prime
    td_std = (ti_prime * td_prime) / (ti_prime + td_prime)

    # Paso 3 — Ganancias estándar
    Ki_std = kp_std / ti_std
    Kd_std = kp_std * td_std

    # Ganancias en formato firmware (para referencia y tabla)
    Kp_fw, Kd_fw, Ki_fw = lambda_a_firmware(kp_std, Kd_std, Ki_std)

    return {
        # Forma serie
        "kc_prime": kc_prime, "ti_prime": ti_prime, "td_prime": td_prime,
        # Forma paralela estándar
        "Kp_std": kp_std, "Ki_std": Ki_std, "Kd_std": Kd_std,
        "ti_std": ti_std, "td_std": td_std,
        # Formato firmware (para tabla de la tesis)
        "Kp": Kp_fw, "Ki": Ki_fw, "Kd": Kd_fw,
        # Parámetros de diseño
        "lambda": lam, "lambda_factor": lambda_factor,
    }


# =============================================================================
# Métricas de desempeño
# =============================================================================
def calcular_metricas(response, setpoint, t):
    """Calcula métricas estándar de respuesta transitoria."""
    N = len(response)

    # Sobreimpulso
    max_val = np.max(response)
    sobreimpulso_pct = max(0.0, (max_val - setpoint) / setpoint * 100.0) if setpoint > 0 else 0.0

    # Tiempo de subida 10%–90%
    y_10, y_90 = 0.1 * setpoint, 0.9 * setpoint
    t_10 = t_90 = None
    for k in range(N):
        if response[k] >= y_10 and t_10 is None:
            t_10 = t[k]
        if response[k] >= y_90 and t_90 is None:
            t_90 = t[k]
    t_rise = (t_90 - t_10) if (t_10 is not None and t_90 is not None) else None

    # Tiempo de asentamiento (banda 2%)
    t_settle = None
    banda = 0.02 * setpoint
    for k in range(N - 1, -1, -1):
        if abs(response[k] - setpoint) > banda:
            if k < N - 1:
                t_settle = t[k + 1]
            break

    # Error en estado estacionario (último 10% de la señal)
    idx_ss = int(0.9 * N)
    e_ss = abs(setpoint - np.mean(response[idx_ss:]))

    return {
        "sobreimpulso_pct": sobreimpulso_pct,
        "tiempo_subida_s": t_rise,
        "tiempo_asentamiento_s": t_settle,
        "error_ss": e_ss,
    }


# =============================================================================
# Variables globales para el PSO
# =============================================================================
g_cv        = None
g_pv        = None
g_pv_smooth = None
g_t         = None
g_ts        = None


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":

    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path  = os.path.join(script_dir, DATA_FILE)

    if not os.path.exists(file_path):
        print(f"ERROR: No se encuentra {file_path}")
        print("Ejecuta primero ControlLazoAbierto.py para generar datos.")
        sys.exit(1)

    print(f"Cargando datos de: {DATA_FILE}...")
    with open(file_path, 'rb') as f:
        cv_all = np.load(f)   # PWM (entrada)
        pv_all = np.load(f)   # m/s (salida)
        t_all  = np.load(f)
        ts_all = np.load(f)

    wheels = ["IZQUIERDA", "DERECHA"]

    # Ganancias PSO finales (de resetPID() en diff_controller.h)
    pso_gains = {
        "IZQUIERDA": {"Kp": 16.0,  "Kd": 20.3,  "Ki": 0.075},
        "DERECHA":   {"Kp": 16.42, "Kd": 20.05, "Ki": 0.001},
    }

    results_all = []

    fig, axes = plt.subplots(2, 2, figsize=(14, 11))
    fig.suptitle(
        f"Comparación PSO vs. Sintonía Lambda (λ = {LAMBDA_FACTOR}τ)",
        fontsize=14, fontweight='bold', y=0.98
    )

    for i, wheel in enumerate(wheels):
        print(f"\n{'='*60}")
        print(f"  RUEDA {wheel}")
        print(f"{'='*60}")

        # ─────────────────────────────────────────────────────────────────
        # Paso 1: Identificar modelo FODT en lazo abierto
        # ─────────────────────────────────────────────────────────────────
        g_cv = cv_all[:, i]
        g_pv = pv_all[:, i]
        g_t  = t_all
        g_pv_smooth = uniform_filter1d(g_pv, size=5)

        if isinstance(ts_all, np.ndarray) and ts_all.ndim > 0:
            g_ts   = ts_all
            ts_val = float(np.mean(ts_all))
        else:
            ts_val = float(ts_all)
            g_ts   = np.full_like(g_t, ts_val)

        # Setpoint = velocidad de estado estacionario medida en lazo abierto
        target_step = float(np.mean(g_pv[g_t >= 7.0]))

        print(">> Identificando modelo FODT (lazo abierto)...")
        pso_id = pso(costFunction_ID, swarmsize=50, npar=3)
        pso_id.run(maxgen=150)
        model_params = pso_id.globalp * SCALE_MODEL
        km, tau, delay = model_params

        # Verificación
        pwm_step = float(np.max(g_cv))
        vss_pred = km * pwm_step
        print(f"   K={km:.6f} m/s/PWM  τ={tau:.4f}s  L={delay:.4f}s")
        print(f"   Verificación: {pwm_step:.0f} PWM × K = {vss_pred:.4f} m/s  "
              f"(esperado: {target_step:.4f} m/s)")

        # ─────────────────────────────────────────────────────────────────
        # Paso 2: Calcular ganancias Lambda
        # Normalizar km: km_norm = km × PWM_NOMINAL ≈ 0.13 m/s
        # ─────────────────────────────────────────────────────────────────
        km_norm = km * PWM_NOMINAL
        print(f"\n>> Calculando ganancias Lambda "
              f"(km_norm={km_norm:.4f}, λ={LAMBDA_FACTOR}τ={LAMBDA_FACTOR*tau:.4f}s)...")
        L_efectivo = max(delay, 2.0 / PID_RATE)
        lambda_result = calcular_ganancias_lambda(km_norm, tau, L_efectivo, LAMBDA_FACTOR)

        print(f"   --- Forma serie (interactuante) ---")
        print(f"   kc' = {lambda_result['kc_prime']:.4f}")
        print(f"   ti' = {lambda_result['ti_prime']:.4f} s")
        print(f"   td' = {lambda_result['td_prime']:.4f} s")
        print(f"   --- Forma paralela estándar ---")
        print(f"   Kp_std = {lambda_result['Kp_std']:.4f}")
        print(f"   Ki_std = {lambda_result['Ki_std']:.6f}")
        print(f"   Kd_std = {lambda_result['Kd_std']:.4f}")
        print(f"   --- Formato firmware (×Ko={ARDUINO_KO:.0f}, escalado a ticks) ---")
        print(f"   Kp_fw = {lambda_result['Kp']:.2f}")
        print(f"   Ki_fw = {lambda_result['Ki']:.4f}")
        print(f"   Kd_fw = {lambda_result['Kd']:.2f}")

        # ─────────────────────────────────────────────────────────────────
        # Paso 3: Simular ambos métodos con simular_pid_firmware
        # Misma planta (model_params), mismas unidades — comparación justa
        # ─────────────────────────────────────────────────────────────────
        ts_pid         = 1.0 / PID_RATE   # 0.0333s — timestep del firmware
        setpoint_signal = np.where(g_t >= 1.0, target_step, 0.0)

        # PSO: ganancias directamente desde resetPID()
        resp_pso = simular_pid_firmware(
            [pso_gains[wheel]["Kp"], pso_gains[wheel]["Kd"], pso_gains[wheel]["Ki"]],
            model_params,
            setpoint_signal, g_t, ts_pid,
            deadband=2    # igual que el firmware real
        )

        # Lambda: ganancias convertidas a formato firmware
        resp_lambda = simular_pid_firmware(
            [lambda_result["Kp"], lambda_result["Kd"], lambda_result["Ki"]],
            model_params,
            setpoint_signal, g_t, ts_pid,
            deadband=0    # Lambda sin deadband para comparación teórica pura
        )

        # ─────────────────────────────────────────────────────────────────
        # Paso 4: Métricas
        # ─────────────────────────────────────────────────────────────────
        met_pso    = calcular_metricas(resp_pso,    target_step, g_t)
        met_lambda = calcular_metricas(resp_lambda, target_step, g_t)

        print(f"\n>> Métricas de desempeño:")
        print(f"   {'Métrica':<32s}  {'PSO':>10s}  {'Lambda':>10s}")
        print(f"   {'-'*56}")
        print(f"   {'Sobreimpulso (%)':<32s}  "
              f"{met_pso['sobreimpulso_pct']:>10.2f}  "
              f"{met_lambda['sobreimpulso_pct']:>10.2f}")
        tr_p = f"{met_pso['tiempo_subida_s']:.3f}"   if met_pso['tiempo_subida_s']   else "N/A"
        tr_l = f"{met_lambda['tiempo_subida_s']:.3f}" if met_lambda['tiempo_subida_s'] else "N/A"
        print(f"   {'Tiempo subida 10-90% (s)':<32s}  {tr_p:>10s}  {tr_l:>10s}")
        ts_p = f"{met_pso['tiempo_asentamiento_s']:.3f}"   if met_pso['tiempo_asentamiento_s']   else "N/A"
        ts_l = f"{met_lambda['tiempo_asentamiento_s']:.3f}" if met_lambda['tiempo_asentamiento_s'] else "N/A"
        print(f"   {'Tiempo asentamiento 2% (s)':<32s}  {ts_p:>10s}  {ts_l:>10s}")
        print(f"   {'Error est. estacionario (m/s)':<32s}  "
              f"{met_pso['error_ss']:>10.5f}  {met_lambda['error_ss']:>10.5f}")

        results_all.append({
            "wheel": wheel,
            "model": {"Km": km, "tau": tau, "L": delay},
            "pso_gains":    {"Kp": pso_gains[wheel]["Kp"],
                             "Ki": pso_gains[wheel]["Ki"],
                             "Kd": pso_gains[wheel]["Kd"]},
            "lambda_gains": {"Kp": lambda_result["Kp"],
                             "Ki": lambda_result["Ki"],
                             "Kd": lambda_result["Kd"]},
            "lambda_gains_std": {"Kp": lambda_result["Kp_std"],
                                 "Ki": lambda_result["Ki_std"],
                                 "Kd": lambda_result["Kd_std"]},
            "met_pso":    met_pso,
            "met_lambda": met_lambda,
        })

        # ─────────────────────────────────────────────────────────────────
        # Paso 5: Graficar
        # ─────────────────────────────────────────────────────────────────
        ax1 = axes[i, 0]
        model_curve = fodt(g_cv, g_t, g_ts, model_params)
        ax1.plot(g_t, g_pv,        'gray', alpha=0.4, linewidth=1, label='Datos reales')
        ax1.plot(g_t, g_pv_smooth, 'k',   alpha=0.8, linewidth=2, label='Datos suavizados')
        ax1.plot(g_t, model_curve, 'r--',            linewidth=2, label='Modelo FODT')
        ax1.text(0.97, 0.05,
                 f"K={km:.5f}  τ={tau:.3f}s  L={delay:.3f}s",
                 transform=ax1.transAxes, fontsize=8, ha='right', va='bottom',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='white',
                           edgecolor='gray', alpha=0.85))
        ax1.set_title(f"Identificación rueda {wheel.lower()} (lazo abierto)",
                      fontsize=11, pad=8)
        ax1.legend(fontsize=8, loc='center right')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylabel("Velocidad (m/s)")
        if i == 1:
            ax1.set_xlabel("Tiempo (s)")

        ax2 = axes[i, 1]
        ax2.axhline(target_step,        color='gray',  linestyle=':',  alpha=0.7, label='Setpoint')
        ax2.axhline(target_step * 1.02, color='green', linestyle=':',  alpha=0.3)
        ax2.axhline(target_step * 0.98, color='green', linestyle=':',  alpha=0.3)
        ax2.plot(g_t, resp_pso,    'b',   linewidth=2,
                 label=f'PSO (Kp={pso_gains[wheel]["Kp"]:.1f})')
        ax2.plot(g_t, resp_lambda, 'r--', linewidth=2,
                 label=f'Lambda (Kp_fw={lambda_result["Kp"]:.1f})')
        ax2.set_title(f"Lazo cerrado rueda {wheel.lower()}: PSO vs Lambda",
                      fontsize=11, pad=8)
        ax2.legend(fontsize=8, loc='upper right')
        ax2.grid(True, alpha=0.3)
        ax2.set_ylabel("Velocidad (m/s)")
        if i == 1:
            ax2.set_xlabel("Tiempo (s)")

    plt.subplots_adjust(top=0.92, bottom=0.07, hspace=0.30, wspace=0.28)
    fig_path = os.path.join(script_dir, "comparacion_pso_vs_lambda.png")
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\n>> Figura guardada en: {fig_path}")
    plt.show()

    # =========================================================================
    # Resumen para la tesis
    # =========================================================================
    print("\n" + "=" * 80)
    print("  RESUMEN PARA LA TESIS (Tabla pid_pso_vs_lambda)")
    print("=" * 80)
    print(f"  {'Método':<16s} {'Kp_fw':>8s} {'Ki_fw':>8s} {'Kd_fw':>8s} "
          f"{'OS(%)':>8s} {'tr(s)':>8s} {'ts(s)':>8s} {'ess':>10s}")
    print(f"  {'-'*80}")

    for r in results_all:
        w  = r["wheel"][:3]
        p  = r["pso_gains"]
        l  = r["lambda_gains"]
        mp = r["met_pso"]
        ml = r["met_lambda"]

        tr_p = f"{mp['tiempo_subida_s']:.3f}"  if mp['tiempo_subida_s']  else "N/A"
        ts_p = f"{mp['tiempo_asentamiento_s']:.3f}" if mp['tiempo_asentamiento_s'] else "N/A"
        tr_l = f"{ml['tiempo_subida_s']:.3f}"  if ml['tiempo_subida_s']  else "N/A"
        ts_l = f"{ml['tiempo_asentamiento_s']:.3f}" if ml['tiempo_asentamiento_s'] else "N/A"

        print(f"  PSO ({w}.)    {p['Kp']:>8.2f} {p['Ki']:>8.4f} {p['Kd']:>8.2f} "
              f"{mp['sobreimpulso_pct']:>8.2f} {tr_p:>8s} {ts_p:>8s} {mp['error_ss']:>10.5f}")
        print(f"  Lambda ({w}.) {l['Kp']:>8.2f} {l['Ki']:>8.4f} {l['Kd']:>8.2f} "
              f"{ml['sobreimpulso_pct']:>8.2f} {tr_l:>8s} {ts_l:>8s} {ml['error_ss']:>10.5f}")

    print()
    for r in results_all:
        diff_os = r["met_lambda"]["sobreimpulso_pct"] - r["met_pso"]["sobreimpulso_pct"]
        sign = "+" if diff_os >= 0 else ""
        print(f"  Rueda {r['wheel']}: Lambda tiene {sign}{diff_os:.2f}% sobreimpulso respecto a PSO")

    print("\n" + "=" * 80)
    print("  NOTA: Kp_fw, Ki_fw, Kd_fw = ganancias en formato firmware.")
    print(f"  Para ganancias estándar dividir por: Ko×PWM_NOMINAL/MPS_TO_TICKS "
          f"= {ARDUINO_KO*PWM_NOMINAL/MPS_TO_TICKS:.2f}")
    print("=" * 80)

    latex_path = os.path.join(script_dir, "resultados_lambda.tex")

    with open(latex_path, 'w', encoding='utf-8') as f:
        f.write("% ============================================================\n")
        f.write("% Resultados generados automáticamente por SintonizacionLambda.py\n")
        f.write(f"% Lambda factor: {LAMBDA_FACTOR}τ  |  PWM_NOMINAL: {PWM_NOMINAL}  |  Ko: {ARDUINO_KO}\n")
        f.write("% ============================================================\n\n")

        # --- Tabla 1: Parámetros FODT ---
        f.write("% --- TABLA: Parámetros FODT identificados en lazo abierto ---\n")
        f.write("\\begin{table}[H]\n\\centering\n")
        f.write("\\caption{Par\\'{a}metros del modelo FODT identificado en lazo abierto.}\n")
        f.write("\\label{tab:fodt_lambda}\n")
        f.write("\\begin{tabular}{lccc}\n\\hline\n")
        f.write("\\textbf{Rueda} & $K_m$ \\textbf{(m/s/PWM)} & $\\tau$ \\textbf{(s)} & $L$ \\textbf{(s)} \\\\\n\\hline\n")
        for r in results_all:
            km  = r["model"]["Km"]
            tau = r["model"]["tau"]
            L   = r["model"]["L"]
            name = "Izquierda" if r["wheel"] == "IZQUIERDA" else "Derecha"
            f.write(f"{name} & {km:.6f} & {tau:.4f} & {L:.4f} \\\\\n")
        f.write("\\hline\n\\end{tabular}\n\\end{table}\n\n")

        # --- Tabla 2: Ganancias PSO vs Lambda (forma estándar) ---
        f.write("% --- TABLA: Ganancias PSO vs Lambda (forma estándar) ---\n")
        f.write("\\begin{table}[H]\n\\centering\n")
        f.write("\\caption{Comparaci\\'{{o}}n de ganancias PID: "
                "firmware definitivo vs.\\ "
                "sinton\\'{{\\i}}a Lambda ($\\lambda = 3\\tau$). "
                "Ganancias en escala est\\'{{a}}ndar Lambda "
                "($K_{{\\mathrm{{std}}}}=K_{{\\mathrm{{fw}}}}/f_\\lambda$, "
                "$f_\\lambda\\approx 22{,}80$).}\n")
        f.write("\\label{tab:comparacion_metodos}\n")
        f.write("\\footnotesize\n")
        f.write("\\begin{tabular}{lcccccc}\n\\hline\n")
        f.write("\\textbf{M\\'{e}todo} & $K_p$ & $K_i$ & $K_d$ & "
                "\\textbf{Sobreimpulso (\\%)} & \\textbf{$t_r$ (s)} & \\textbf{$e_{ss}$ (m/s)} \\\\\n\\hline\n")

        for r in results_all:
            name  = "izq." if r["wheel"] == "IZQUIERDA" else "der."
            # Firmware (valores definitivos de resetPID()) → forma estándar Lambda
            # Kp y Kd: K_std = K_fw / factor
            # Ki: inversa de lambda_a_firmware donde ki_fw = ki_std * factor * ts_pid
            #     → ki_std = ki_fw / (factor * ts_pid)
            factor = ARDUINO_KO * PWM_NOMINAL / MPS_TO_TICKS
            ts_pid_conv = 1.0 / PID_RATE   # 0.0333 s — mismo factor que lambda_a_firmware
            kp_pso_std = r["pso_gains"]["Kp"] / factor
            ki_pso_std = r["pso_gains"]["Ki"] / (factor * ts_pid_conv)
            kd_pso_std = r["pso_gains"]["Kd"] / factor
            mp  = r["met_pso"]
            tr_p = f"{mp['tiempo_subida_s']:.3f}" if mp["tiempo_subida_s"] else "N/A"
            f.write(f"Firmware ({name}) & "
                    f"{kp_pso_std:.4f} & {ki_pso_std:.5f} & {kd_pso_std:.4f} & "
                    f"{mp['sobreimpulso_pct']:.2f} & {tr_p} & {mp['error_ss']:.5f} \\\\\n")
            # Lambda
            kp_l = r["lambda_gains_std"]["Kp"]
            ki_l = r["lambda_gains_std"]["Ki"]
            kd_l = r["lambda_gains_std"]["Kd"]
            ml   = r["met_lambda"]
            tr_l = f"{ml['tiempo_subida_s']:.3f}" if ml["tiempo_subida_s"] else "N/A"
            f.write(f"Lambda ({name}) & "
                    f"{kp_l:.4f} & {ki_l:.5f} & {kd_l:.4f} & "
                    f"{ml['sobreimpulso_pct']:.2f} & {tr_l} & {ml['error_ss']:.5f} \\\\\n")
            f.write("\\hline\n")

        f.write("\\end{tabular}\n\\end{table}\n\n")

        # --- Tabla 3: Métricas completas ---
        f.write("% --- TABLA: Métricas completas de desempeño ---\n")
        f.write("\\begin{table}[H]\n\\centering\n")
        f.write("\\caption{M\\'{e}tricas de desempe\\~{n}o: Firmware vs.\\ Lambda ($\\lambda=3\\tau$).}\n")
        f.write("\\label{tab:metricas_comparacion}\n")
        f.write("\\begin{tabular}{llcccc}\n\\hline\n")
        f.write("\\textbf{Rueda} & \\textbf{M\\'{e}todo} & "
                "\\textbf{OS (\\%)} & \\textbf{$t_r$ (s)} & "
                "\\textbf{$t_s$ (s)} & \\textbf{$e_{ss}$ (m/s)} \\\\\n\\hline\n")
        for r in results_all:
            name = "Izquierda" if r["wheel"] == "IZQUIERDA" else "Derecha"
            mp = r["met_pso"]
            ml = r["met_lambda"]
            tr_p = f"{mp['tiempo_subida_s']:.3f}"        if mp["tiempo_subida_s"]        else "N/A"
            ts_p = f"{mp['tiempo_asentamiento_s']:.3f}"  if mp["tiempo_asentamiento_s"]  else "N/A"
            tr_l = f"{ml['tiempo_subida_s']:.3f}"        if ml["tiempo_subida_s"]        else "N/A"
            ts_l = f"{ml['tiempo_asentamiento_s']:.3f}"  if ml["tiempo_asentamiento_s"]  else "N/A"
            f.write(f"\\multirow{{2}}{{*}}{{{name}}} & Firmware & "
                    f"{mp['sobreimpulso_pct']:.2f} & {tr_p} & {ts_p} & {mp['error_ss']:.5f} \\\\\n")
            f.write(f" & Lambda & "
                    f"{ml['sobreimpulso_pct']:.2f} & {tr_l} & {ts_l} & {ml['error_ss']:.5f} \\\\\n")
            f.write("\\hline\n")
        f.write("\\end{tabular}\n\\end{table}\n\n")

        # --- Resumen textual ---
        f.write("% --- TEXTO: Diferencias de sobreimpulso ---\n")
        for r in results_all:
            diff_os = r["met_lambda"]["sobreimpulso_pct"] - r["met_pso"]["sobreimpulso_pct"]
            diff_tr = ((r["met_pso"]["tiempo_subida_s"] or 0) -
                       (r["met_lambda"]["tiempo_subida_s"] or 0))
            name = "izquierda" if r["wheel"] == "IZQUIERDA" else "derecha"
            f.write(f"% Rueda {name}: Lambda +{diff_os:.2f}% sobreimpulso, "
                    f"Lambda {diff_tr:.3f}s más rápida en subida\n")

    print(f"\n>> Resultados LaTeX guardados en: {latex_path}")