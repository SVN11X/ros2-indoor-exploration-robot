from pyPso import *
import matplotlib.pyplot as plt
import numpy as np
import os
from scipy.ndimage import uniform_filter1d

# ==============================================================================
#  CONFIGURACIÓN GLOBAL
# ==============================================================================
# Con lazo abierto, la entrada al FODT es PWM (0-255) y la salida es m/s.
# K ahora tiene unidades [m/s per PWM], típicamente ~0.001 para estos motores.
SCALE_MODEL = np.array([0.01, 2.0, 0.5])  # [K en m/s/PWM, Tau s, Delay s]

SCALE_KP = 40.0
SCALE_KD = 25.0
SCALE_KI = 0.05

MAX_PWM    = 255.0
ARDUINO_KO = 50.0
DEADBAND   = 2

WHEEL_DIAMETER    = 0.067
ENC_TICKS_PER_REV = 1980
PID_RATE          = 30
MPS_TO_TICKS = ENC_TICKS_PER_REV / (np.pi * WHEEL_DIAMETER * PID_RATE)

DATA_LAZO_ABIERTO = "step_response_velocity_lazo_abierto.npy"
# ==============================================================================
#  MODELO FODT — entrada PWM, salida m/s
# ==============================================================================
def fodt(cv_pwm, t, ts, params):
    """
    cv_pwm: señal de entrada en PWM (0-255)
    salida: velocidad en m/s
    K tiene unidades m/s por unidad de PWM
    """
    km, tau, delay = params
    N = len(t)
    pv_est = np.zeros(N)
    if tau < 0.001: tau = 0.001
    for k in range(1, N):
        dt = float(ts[k]) if hasattr(ts, '__len__') else float(ts)
        steps_back = int(delay / dt)
        idx_delay  = max(k - steps_back, 0)
        u_delayed  = cv_pwm[idx_delay]
        pv_est[k]  = pv_est[k-1] + (dt / tau) * (km * u_delayed - pv_est[k-1])
    return pv_est

def costFunction_ID(x):
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

# ==============================================================================
#  SIMULACIÓN PID — FODT con entrada PWM (coherente con lazo abierto)
# ==============================================================================
def simular_pid_firmware(pid_params, model_params, cv_signal_mps, t, ts_val, deadband=0):
    kp, kd, ki = pid_params
    km, tau, delay = model_params

    # Si ts_val es el timestep del firmware (0.033s), crear vector de tiempo propio
    t_sim = np.arange(t[0], t[-1] + ts_val, ts_val)
    N     = len(t_sim)

    pv_sim     = np.zeros(N)
    output     = 0.0
    ITerm      = 0.0
    prev_input = 0

    if tau < 1e-4: tau = 1e-4
    delay_steps = int(delay / ts_val)

    for k in range(1, N):
        # Interpolar setpoint al tiempo actual del firmware
        setpoint_k = float(np.interp(t_sim[k], t, cv_signal_mps))

        # Planta FODT
        pv_sim[k] = pv_sim[k-1] + (ts_val / tau) * (km * output - pv_sim[k-1])
        pv_sim[k] = max(0.0, pv_sim[k])

        # Ticks
        target_ticks  = setpoint_k * MPS_TO_TICKS
        current_input = int(round(pv_sim[k] * MPS_TO_TICKS))
        Perror        = target_ticks - current_input

        if abs(Perror) <= deadband:
            Perror = 0

        delta_u = (kp * Perror - kd * (current_input - prev_input) + ITerm) / ARDUINO_KO
        output += delta_u

        if output >= MAX_PWM:
            output = MAX_PWM
        elif output <= -MAX_PWM:
            output = -MAX_PWM
        else:
            ITerm += ki * Perror

        prev_input = current_input

    # Remuestrear la respuesta al tiempo original (10Hz) para comparar con datos
    pv_resampled = np.interp(t, t_sim, pv_sim)
    return pv_resampled


def costFunction_PID(x):
    cost   = np.zeros(x.shape[0])
    target = float(np.max(g_cv_setpoint))
    w_mse  = 1.0
    w_OS = 3.0

    # Timestep del firmware (30Hz), no el de muestreo (10Hz)
    ts_pid = 1.0 / PID_RATE   # 0.0333s

    for i in range(x.shape[0]):
        # --- Acotar partículas a [0, 1] antes de escalar ---
        x_clamped = np.clip(x[i], 0.0001, 1.0)
        kp = x_clamped[0] * SCALE_KP
        kd = x_clamped[1] * SCALE_KD
        ki = x_clamped[2] * SCALE_KI

        try:
            response = simular_pid_firmware(
                [kp, kd, ki], g_best_model,
                g_cv_setpoint, g_t,
                ts_pid,          # ← 0.0333s en lugar de 0.1s
                deadband=DEADBAND
            )
        except Exception:
            cost[i] = 1e6
            continue

        if np.any(np.isnan(response)) or np.any(np.isinf(response)):
            cost[i] = 1e6
            continue

        error     = target - response
        mse       = np.mean(error ** 2)
        overshoot = max(0.0, float(np.max(response)) - target)
        cost[i]   = w_mse * mse + w_OS * overshoot ** 2

    return cost

# ==============================================================================
#  PROGRAMA PRINCIPAL
# ==============================================================================
g_cv = None; g_pv = None; g_pv_smooth = None; g_cv_setpoint = None
g_t  = None; g_ts = None; g_best_model = None

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path  = os.path.join(script_dir, DATA_LAZO_ABIERTO)

    if not os.path.exists(file_path):
        print(f"ERROR: No se encuentra {file_path}")
        exit()

    print("Cargando datos de lazo abierto...")
    with open(file_path, 'rb') as f:
        cv_all = np.load(f)   # PWM
        pv_all = np.load(f)   # m/s
        t_all  = np.load(f)
        ts_all = np.load(f)

    wheels     = ["IZQUIERDA", "DERECHA"]
    final_pids = []
    plt.figure(figsize=(14, 11))

    best_models = []

    for i in range(2):
        print(f"\n{'='*50}")
        print(f" PROCESANDO RUEDA {wheels[i]}")
        print(f"{'='*50}")

        g_cv = cv_all[:, i]   # PWM (entrada al FODT)
        g_pv = pv_all[:, i]   # m/s (salida medida)
        g_t  = t_all

        if isinstance(ts_all, np.ndarray) and ts_all.ndim > 0:
            g_ts   = ts_all
            ts_val = float(np.mean(ts_all))
        else:
            ts_val = float(ts_all)
            g_ts   = np.full_like(g_t, ts_val)

        # Suavizar solo la salida para identificación más limpia
        g_pv_smooth = uniform_filter1d(g_pv, size=5)

        # Setpoint en m/s para la etapa de optimización PID
        # Usamos la velocidad de estado estacionario medida como target
        vss = np.mean(g_pv[g_t >= 7.0])
        g_cv_setpoint        = np.zeros_like(g_t)
        g_cv_setpoint[g_t >= 1.0] = vss
        print(f"   Velocidad estado estacionario detectada: {vss:.4f} m/s")

        # --- Etapa 1: Identificación FODT (entrada PWM → salida m/s) ---
        print(">> Etapa 1: Identificando modelo FODT (lazo abierto)...")
        pso_id = pso(costFunction_ID, swarmsize=50, npar=3)
        pso_id.run(maxgen=150)
        g_best_model = pso_id.globalp * SCALE_MODEL
        print(f"   K={g_best_model[0]:.6f} m/s/PWM  Tau={g_best_model[1]:.4f}s  Delay={g_best_model[2]:.4f}s")

        # Verificación: PWM * K debe dar ~vss
        pwm_step = np.max(g_cv)
        vss_pred = g_best_model[0] * pwm_step
        print(f"   Verificación: {pwm_step:.0f} PWM × K = {vss_pred:.4f} m/s  (esperado: {vss:.4f} m/s)")

        ax1 = plt.subplot(2, 2, i*2 + 1)
        model_curve = fodt(g_cv, g_t, g_ts, g_best_model)
        ax1.plot(g_t, g_pv,        'gray', label='Datos reales',    alpha=0.4, linewidth=1)
        ax1.plot(g_t, g_pv_smooth, 'k',    label='Datos suavizados',alpha=0.8, linewidth=2)
        ax1.plot(g_t, model_curve, 'r--',  label='Modelo FODT',     linewidth=2)
        ax1.text(0.97, 0.05,
                 f"K={g_best_model[0]:.5f}  τ={g_best_model[1]:.3f}s  L={g_best_model[2]:.3f}s",
                 transform=ax1.transAxes, fontsize=8, ha='right', va='bottom',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.85))
        ax1.set_title(f"Identificación rueda {wheels[i].lower()} (lazo abierto)", fontsize=11)
        ax1.legend(fontsize=8); ax1.grid(True, alpha=0.3)
        ax1.set_ylabel("Velocidad (m/s)")
        if i == 1: ax1.set_xlabel("Tiempo (s)")

        # --- Etapa 2: Optimización PID ---
        print(">> Etapa 2: Optimizando ganancias PID...")
        pso_pid = pso(costFunction_PID, swarmsize=50, npar=3)
        pso_pid.run(maxgen=150)

        kp_opt = pso_pid.globalp[0] * SCALE_KP
        kd_opt = pso_pid.globalp[1] * SCALE_KD
        ki_opt = pso_pid.globalp[2] * SCALE_KI
        print(f"   Kp={kp_opt:.3f}  Kd={kd_opt:.3f}  Ki={ki_opt:.5f}")
        final_pids.append([kp_opt, kd_opt, ki_opt])

        ax2 = plt.subplot(2, 2, i*2 + 2)
        sim_response = simular_pid_firmware(
            [kp_opt, kd_opt, ki_opt], g_best_model,
            g_cv_setpoint, g_t, ts_val, deadband=DEADBAND
        )
        ax2.axhline(vss, color='g', linestyle='--', label=f'Target ({vss:.3f} m/s)')
        ax2.plot(g_t, g_pv,        'gray', alpha=0.4, linewidth=1, label='Real (lazo abierto)')
        ax2.plot(g_t, sim_response, 'b',   linewidth=2, label='Simulación PID')
        ax2.text(0.97, 0.05,
                 f"Kp={kp_opt:.1f}  Kd={kd_opt:.1f}  Ki={ki_opt:.4f}",
                 transform=ax2.transAxes, fontsize=8, ha='right', va='bottom',
                 bbox=dict(boxstyle='round,pad=0.3', facecolor='white', edgecolor='gray', alpha=0.85))
        ax2.set_title(f"Control simulado rueda {wheels[i].lower()}", fontsize=11)
        ax2.legend(fontsize=8); ax2.grid(True, alpha=0.3)
        ax2.set_ylabel("Velocidad (m/s)")
        if i == 1: ax2.set_xlabel("Tiempo (s)")

        best_models.append(g_best_model.tolist())

    plt.suptitle("Identificación FODT (lazo abierto) y sintonización PID por PSO",
                 fontsize=13, fontweight='bold', y=0.98)
    plt.subplots_adjust(top=0.92, bottom=0.07, hspace=0.30, wspace=0.28)

    fig_path = os.path.join(script_dir, "identificacion_y_sintonizacion_pso.png")
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"\n>> Figura guardada en: {fig_path}")
    plt.close()

    # --- Resultado final ---
    ko_val = int(ARDUINO_KO)
    izq    = final_pids[0]
    der    = final_pids[1]
    print("\n" + "="*70)
    print(" COMANDO PARA ARDUINO:")
    print(f" z {izq[0]:.2f}:{izq[1]:.2f}:{izq[2]:.4f}:{ko_val}"
          f":{der[0]:.2f}:{der[1]:.2f}:{der[2]:.4f}:{ko_val}")
    print("="*70)
    print("\n VALORES PARA resetPID():")
    print(f"   leftPID  → Kp={izq[0]:.2f}  Kd={izq[1]:.2f}  Ki={izq[2]:.5f}  Ko={ko_val}")
    print(f"   rightPID → Kp={der[0]:.2f}  Kd={der[1]:.2f}  Ki={der[2]:.5f}  Ko={ko_val}")

    latex_path = os.path.join(script_dir, "resultados_pso.tex")
 
    with open(latex_path, 'w', encoding='utf-8') as f:
 
        # ---- Encabezado -------------------------------------------------------
        f.write("% ==============================================================\n")
        f.write("% Resultados generados automáticamente por SintonizacionAutomatica.py\n")
        f.write(f"% PWM_STEP nominal: calculado del dato  |  Ko: {int(ARDUINO_KO)}\n")
        f.write("% ==============================================================\n\n")
 
        # ---- Tabla 1: Parámetros FODT identificados ---------------------------
        f.write("% --- TABLA 1: Parámetros del modelo FODT identificado en lazo abierto ---\n")
        f.write("\\begin{table}[H]\n")
        f.write("\\centering\n")
        f.write("\\caption{Par\\'{a}metros del modelo FODT identificado en lazo abierto "
                "mediante PSO (\\texttt{SintonizacionAutomatica.py}).}\n")
        f.write("\\label{tab:fodt_auto}\n")
        f.write("\\begin{tabular}{lccc}\n")
        f.write("\\hline\n")
        f.write("\\textbf{Rueda} & "
                "$K_m$ \\textbf{(m/s/PWM)} & "
                "$\\tau$ \\textbf{(s)} & "
                "$L$ \\textbf{(s)} \\\\\n")
        f.write("\\hline\n")
 
        wheel_names_es = ["Izquierda", "Derecha"]
        for i, (name, model) in enumerate(zip(wheel_names_es, best_models)):
            km, tau, delay = model
            f.write(f"{name} & "
                    f"${km:.6f}$ & "
                    f"${tau:.4f}$ & "
                    f"${delay:.4f}$ \\\\\n")
 
        f.write("\\hline\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n\n")
 
        # ---- Tabla 2: Ganancias PID sugeridas por PSO -------------------------
        f.write("% --- TABLA 2: Ganancias PID iniciales sugeridas por PSO ---\n")
        f.write("\\begin{table}[H]\n")
        f.write("\\centering\n")
        f.write("\\caption{Ganancias PID sugeridas por PSO como punto de partida "
                "para el refinamiento experimental. "
                "Los valores definitivos del firmware pueden diferir tras el ajuste iterativo "
                "con \\texttt{ControlLazoCerrado.py} "
                "(v\\'{e}ase la Tabla~\\ref{tab:pid_pso_results}).}\n")
        f.write("\\label{tab:pid_auto_inicial}\n")
        f.write("\\begin{tabular}{lcccc}\n")
        f.write("\\hline\n")
        f.write("\\textbf{Rueda} & "
                "$K_p$ & $K_d$ & $K_i$ & $K_o$ \\\\\n")
        f.write("\\hline\n")
 
        for name, pid in zip(wheel_names_es, final_pids):
            kp, kd, ki = pid
            f.write(f"{name} & "
                    f"${kp:.2f}$ & "
                    f"${kd:.2f}$ & "
                    f"${ki:.5f}$ & "
                    f"${int(ARDUINO_KO)}$ \\\\\n")
 
        f.write("\\hline\n")
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n\n")
 
        # ---- Tabla 3: Comparación PSO sugerido vs firmware definitivo ---------
        # Rellenar manualmente con los valores finales de diff_controller.h
        f.write("% --- TABLA 3: PSO sugerido vs. ganancias definitivas del firmware ---\n")
        f.write("% INSTRUCCIÓN: completar la columna 'Firmware' con los valores reales\n")
        f.write("%              de resetPID() en diff_controller.h.\n")
        f.write("\\begin{table}[H]\n")
        f.write("\\centering\n")
        f.write("\\caption{Comparaci\\'{o}n entre las ganancias PID sugeridas por PSO "
                "y los valores definitivos cargados en el firmware tras el refinamiento "
                "experimental iterativo.}\n")
        f.write("\\label{tab:auto_vs_firmware}\n")
        f.write("\\begin{tabular}{llcccc}\n")
        f.write("\\hline\n")
        f.write("\\textbf{Rueda} & \\textbf{Origen} & "
                "$K_p$ & $K_d$ & $K_i$ & $K_o$ \\\\\n")
        f.write("\\hline\n")
 
        # Valores definitivos del firmware (diff_controller.h)
        firmware_gains = {
            "Izquierda": (16.0,  20.3,  0.075, 50),
            "Derecha":   (16.42, 20.05, 0.001, 50),
        }
 
        for name, pid in zip(wheel_names_es, final_pids):
            kp_pso, kd_pso, ki_pso = pid
            kp_fw, kd_fw, ki_fw, ko_fw = firmware_gains[name]
 
            # Fila PSO sugerido
            f.write(f"\\multirow{{2}}{{*}}{{{name}}} & "
                    f"PSO (inicial) & "
                    f"${kp_pso:.2f}$ & "
                    f"${kd_pso:.2f}$ & "
                    f"${ki_pso:.5f}$ & "
                    f"${int(ARDUINO_KO)}$ \\\\\n")
            # Fila firmware definitivo
            f.write(f" & Firmware (final) & "
                    f"${kp_fw:.2f}$ & "
                    f"${kd_fw:.2f}$ & "
                    f"${ki_fw:.3f}$ & "
                    f"${ko_fw}$ \\\\\n")
            f.write("\\hline\n")
 
        f.write("\\end{tabular}\n")
        f.write("\\end{table}\n")
 
    print(f"\n>> Tablas LaTeX guardadas en: {latex_path}")