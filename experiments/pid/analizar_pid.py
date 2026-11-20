#!/usr/bin/env python3
import sys
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from scipy.optimize import minimize, differential_evolution
from scipy.signal import lti, step as scipy_step
import csv
from datetime import datetime

plt.rcParams.update({
    'font.size': 10,
    'font.family': 'DejaVu Sans',
    'axes.grid': True,
    'grid.alpha': 0.3,
    'figure.dpi': 150,
})
REF_VEL    = 0.13
KP_IZQ     = 16.00
KI_IZQ     = 0.075
KD_IZQ     = 20.3
KP_DER     = 16.42
KI_DER     = 0.001
KD_DER     = 20.05
KO         = 1.0
BANDA_TS   = 0.02
OUTDIR     = os.path.dirname(os.path.abspath(__file__))
def cargar_datos(path):

    data = np.load(path, allow_pickle=True)
    if isinstance(data, np.ndarray) and data.dtype == object:
        data = data.item()

    if isinstance(data, dict):
        t     = np.array(data.get('t', data.get('time', data.get('timestamp', None))))
        left  = np.array(data.get('left', data.get('vel_izq', data.get('velocidad_izq', None))))
        right = np.array(data.get('right', data.get('vel_der', data.get('velocidad_der', left))))
        if t is None:
            t = np.arange(len(left)) * 0.05
    elif isinstance(data, np.ndarray):
        if data.ndim == 2 and data.shape[1] >= 3:
            t, left, right = data[:, 0], data[:, 1], data[:, 2]
        elif data.ndim == 2 and data.shape[1] == 2:
            left, right = data[:, 0], data[:, 1]
            t = np.arange(len(left)) * 0.05
        else:
            left = data.flatten()
            right = left.copy()
            t = np.arange(len(left)) * 0.05
    else:
        raise ValueError(f"Formato desconocido en {path}")

    return t, left, right
def calcular_metricas(t, y, ref):

    N   = len(y)
    dt  = t[1] - t[0] if len(t) > 1 else 0.05
    ref = float(ref)
    Mp = max(0.0, (np.max(y) - ref) / ref * 100.0)
    t10 = next((t[k] for k in range(N) if y[k] >= 0.10 * ref), np.nan)
    t90 = next((t[k] for k in range(N) if y[k] >= 0.90 * ref), np.nan)
    tr  = (t90 - t10) if not (np.isnan(t10) or np.isnan(t90)) else np.nan
    banda    = BANDA_TS * ref
    violados = np.where(np.abs(y - ref) > banda)[0]
    if len(violados) > 0:
        k_star = violados[-1]
        ts = t[k_star + 1] if k_star + 1 < N else t[-1]
    else:
        ts = t[0]
    N_ss = int(0.9 * N)
    ess  = abs(ref - np.mean(y[N_ss:]))

    return {'Mp': Mp, 'tr': tr, 'ts': ts, 'ess': ess}
def respuesta_fodt_step(t, K, tau, L, ref):

    y = np.zeros_like(t)
    mask = t >= L
    y[mask] = K * ref * (1.0 - np.exp(-(t[mask] - L) / tau))
    return y

def identificar_fodt(t, y, ref):

    def mse(params):
        K, tau, L = params
        if K <= 0 or tau <= 0 or L < 0:
            return 1e9
        y_hat = respuesta_fodt_step(t, K, tau, L, ref)
        return np.mean((y - y_hat) ** 2)

    bounds = [(0.1, 5.0), (0.01, 5.0), (0.0, 2.0)]
    result = differential_evolution(mse, bounds, seed=42, maxiter=1000,
                                    tol=1e-8, workers=1)
    K, tau, L = result.x
    return K, tau, L
def lambda_tuning(K, tau, L, factor=3.0):

    lam = factor * tau
    Kc  = tau / (K * (lam + L))
    Ti  = tau
    Td  = L / 2.0
    Kp = Kc
    Ki = Kc / Ti if Ti > 0 else 0.0
    Kd = Kc * Td
    return {'Kc': Kc, 'Ti': Ti, 'Td': Td, 'Kp': Kp, 'Ki': Ki, 'Kd': Kd}
def simular_pid_lc(t, K, tau, L, Kp, Ki, Kd, ref, Ko=1.0):

    dt = t[1] - t[0]
    N  = len(t)
    delay_steps = max(1, int(round(L / dt)))
    u_buf = np.zeros(delay_steps + 1)

    y       = np.zeros(N)
    e_prev  = 0.0
    e_int   = 0.0

    for k in range(1, N):
        e      = ref - y[k - 1]
        e_int += e * dt
        e_der  = (e - e_prev) / dt
        u_raw  = (Kp * e + Ki * e_int + Kd * e_der) / Ko
        u      = np.clip(u_raw, -255.0, 255.0)
        if abs(u_raw) > 255.0:
            e_int -= e * dt

        u_buf  = np.roll(u_buf, 1)
        u_buf[0] = u
        y[k] = (1.0 - dt / tau) * y[k - 1] + (K * dt / tau) * Ko * u_buf[-1]
        e_prev = e

    return y
def plot_escalon(t, y_izq, y_der, K_i, tau_i, L_i, K_d, tau_d, L_d,
                 Kp_i, Ki_i, Kd_i, Kp_d, Ki_d, Kd_d, path_out):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)
    titles  = ['Rueda Izquierda', 'Rueda Derecha']
    ys      = [y_izq, y_der]
    params  = [(K_i, tau_i, L_i, Kp_i, Ki_i, Kd_i),
               (K_d, tau_d, L_d, Kp_d, Ki_d, Kd_d)]

    for ax, title, y_real, (K, tau, L, Kp, Ki, Kd) in zip(axes, titles, ys, params):
        y_fodt = respuesta_fodt_step(t, K, tau, L, REF_VEL)
        ax.axhline(REF_VEL, color='gray', lw=1.2, ls='--', label='Referencia')
        ax.axhspan(REF_VEL * (1 - BANDA_TS), REF_VEL * (1 + BANDA_TS),
                   alpha=0.12, color='green', label='Banda ±2%')
        ax.plot(t, y_real, color='steelblue', lw=1.6, label='Respuesta real')
        ax.plot(t, y_fodt, color='coral',     lw=1.2, ls=':', label='Modelo FODT')
        ax.set_title(title)
        ax.set_xlabel('Tiempo (s)')
        ax.set_ylabel('Velocidad (m/s)')
        ax.legend(fontsize=8)
        ax.set_xlim(t[0], t[-1])

    fig.suptitle(f'Respuesta al escalón PID — ref = {REF_VEL} m/s', fontweight='bold')
    fig.tight_layout()
    fig.savefig(path_out, bbox_inches='tight')
    plt.close(fig)
    print(f'  ✓ {path_out}')
def plot_pso_vs_lambda(t, lam_gains_i, lam_gains_d,
                       K_i, tau_i, L_i, K_d, tau_d, L_d, path_out):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=False)
    titles  = ['Rueda Izquierda', 'Rueda Derecha']
    fodt_p  = [(K_i, tau_i, L_i), (K_d, tau_d, L_d)]
    pso_g   = [(KP_IZQ, KI_IZQ, KD_IZQ), (KP_DER, KI_DER, KD_DER)]
    lam_g   = [lam_gains_i, lam_gains_d]

    for ax, title, (K, tau, L), (Kp_p, Ki_p, Kd_p), lg in \
            zip(axes, titles, fodt_p, pso_g, lam_g):
        y_pso = simular_pid_lc(t, K, tau, L, Kp_p, Ki_p, Kd_p, REF_VEL, KO)
        y_lam = simular_pid_lc(t, K, tau, L, lg['Kp'], lg['Ki'], lg['Kd'], REF_VEL, KO)

        ax.axhline(REF_VEL, color='gray', lw=1.2, ls='--', label='Referencia')
        ax.axhspan(REF_VEL * (1 - BANDA_TS), REF_VEL * (1 + BANDA_TS),
                   alpha=0.12, color='green', label='Banda ±2%')
        ax.plot(t, y_pso, color='steelblue', lw=1.8, label='PSO refinado')
        ax.plot(t, y_lam, color='coral',     lw=1.8, label=r'Lambda ($\lambda=3\tau$)')
        ax.set_title(title)
        ax.set_xlabel('Tiempo (s)')
        ax.set_ylabel('Velocidad (m/s)')
        ax.legend(fontsize=8)
        ax.set_xlim(t[0], t[-1])

    fig.suptitle('Comparación PSO refinado vs sintonía Lambda', fontweight='bold')
    fig.tight_layout()
    fig.savefig(path_out, bbox_inches='tight')
    plt.close(fig)
    print(f'  ✓ {path_out}')
def generar_latex(K_i, tau_i, L_i, K_d, tau_d, L_d,
                  met_pso_i, met_pso_d,
                  lam_i, lam_d,
                  met_lam_i, met_lam_d):
    lines = []
    lines.append("% ═══════════════════════════════════════════════════")
    lines.append(f"% Generado automáticamente por analizar_pid.py")
    lines.append(f"% {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("% ═══════════════════════════════════════════════════\n")
    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    lines.append(r"\caption{Parámetros del modelo FODT identificado (lazo cerrado, ganancias definitivas).}")
    lines.append(r"\label{tab:fodt_params}")
    lines.append(r"\begin{tabular}{lccc}")
    lines.append(r"\hline")
    lines.append(r"\textbf{Rueda} & $K_m$ & $\tau$ (s) & $L$ (s) \\")
    lines.append(r"\hline")
    lines.append(f"Izquierda & {K_i:.4f} & {tau_i:.4f} & {L_i:.4f} \\\\")
    lines.append(f"Derecha   & {K_d:.4f} & {tau_d:.4f} & {L_d:.4f} \\\\")
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}" + "\n")
    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    lines.append(r"\caption{Indicadores de desempeño del controlador PID con ganancias finales.}")
    lines.append(r"\label{tab:pid_performance}")
    lines.append(r"\begin{tabular}{lcc}")
    lines.append(r"\hline")
    lines.append(r"\textbf{Indicador} & \textbf{Rueda izquierda} & \textbf{Rueda derecha} \\")
    lines.append(r"\hline")
    tr_i = f"{met_pso_i['tr']:.3f}" if not np.isnan(met_pso_i['tr']) else "---"
    tr_d = f"{met_pso_d['tr']:.3f}" if not np.isnan(met_pso_d['tr']) else "---"
    lines.append(f"Tiempo de subida (10\\%--90\\%) & {tr_i}~s & {tr_d}~s \\\\")
    lines.append(f"Tiempo de establecimiento (2\\%) & {met_pso_i['ts']:.3f}~s & {met_pso_d['ts']:.3f}~s \\\\")
    lines.append(f"Sobreimpulso máximo & {met_pso_i['Mp']:.2f}~\\% & {met_pso_d['Mp']:.2f}~\\% \\\\")
    lines.append(f"Error en estado estacionario & {met_pso_i['ess']:.4f}~m/s & {met_pso_d['ess']:.4f}~m/s \\\\")
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}" + "\n")
    lines.append(r"\begin{table}[H]")
    lines.append(r"\centering")
    lines.append(r"\caption{Comparación de ganancias PID: PSO vs.\ Lambda ($\lambda = 3\tau$).}")
    lines.append(r"\label{tab:pid_pso_vs_lambda}")
    lines.append(r"\begin{tabular}{lcccccc}")
    lines.append(r"\hline")
    lines.append(r"\textbf{Método} & $K_p$ & $K_i$ & $K_d$ & \textbf{Mp (\%)} & \textbf{$t_s$ (s)} & \textbf{$e_{ss}$ (m/s)} \\")
    lines.append(r"\hline")

    def fmt(v, d=3):
        return f"{v:.{d}f}"

    lines.append(f"PSO refinado (izq.) & {KP_IZQ} & {KI_IZQ} & {KD_IZQ} & "
                 f"{fmt(met_pso_i['Mp'],2)} & {fmt(met_pso_i['ts'],3)} & {fmt(met_pso_i['ess'],4)} \\\\")
    lines.append(f"Lambda (izq.)       & {fmt(lam_i['Kp'],4)} & {fmt(lam_i['Ki'],4)} & "
                 f"{fmt(lam_i['Kd'],4)} & {fmt(met_lam_i['Mp'],2)} & "
                 f"{fmt(met_lam_i['ts'],3)} & {fmt(met_lam_i['ess'],4)} \\\\")
    lines.append(r"\hline")
    lines.append(f"PSO refinado (der.) & {KP_DER} & {KI_DER} & {KD_DER} & "
                 f"{fmt(met_pso_d['Mp'],2)} & {fmt(met_pso_d['ts'],3)} & {fmt(met_pso_d['ess'],4)} \\\\")
    lines.append(f"Lambda (der.)       & {fmt(lam_d['Kp'],4)} & {fmt(lam_d['Ki'],4)} & "
                 f"{fmt(lam_d['Kd'],4)} & {fmt(met_lam_d['Mp'],2)} & "
                 f"{fmt(met_lam_d['ts'],3)} & {fmt(met_lam_d['ess'],4)} \\\\")
    lines.append(r"\hline")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    return "\n".join(lines)
def guardar_csv(met_pso_i, met_pso_d, lam_i, lam_d, met_lam_i, met_lam_d,
                K_i, tau_i, L_i, K_d, tau_d, L_d, path_out):
    rows = [
        ['Rueda', 'Método', 'Kp', 'Ki', 'Kd', 'Mp_%', 'tr_s', 'ts_s', 'ess_ms',
         'K_fodt', 'tau_fodt_s', 'L_fodt_s'],
        ['Izquierda', 'PSO', KP_IZQ, KI_IZQ, KD_IZQ,
         met_pso_i['Mp'], met_pso_i['tr'], met_pso_i['ts'], met_pso_i['ess'],
         K_i, tau_i, L_i],
        ['Izquierda', 'Lambda', lam_i['Kp'], lam_i['Ki'], lam_i['Kd'],
         met_lam_i['Mp'], met_lam_i['tr'], met_lam_i['ts'], met_lam_i['ess'],
         K_i, tau_i, L_i],
        ['Derecha', 'PSO', KP_DER, KI_DER, KD_DER,
         met_pso_d['Mp'], met_pso_d['tr'], met_pso_d['ts'], met_pso_d['ess'],
         K_d, tau_d, L_d],
        ['Derecha', 'Lambda', lam_d['Kp'], lam_d['Ki'], lam_d['Kd'],
         met_lam_d['Mp'], met_lam_d['tr'], met_lam_d['ts'], met_lam_d['ess'],
         K_d, tau_d, L_d],
    ]
    with open(path_out, 'w', newline='') as f:
        csv.writer(f).writerows(rows)
    print(f'  ✓ {path_out}')
def main():
    npy_path = sys.argv[1] if len(sys.argv) > 1 else 'step_response_velocity.npy'
    if not os.path.exists(npy_path):
        for candidate in ['test/pid/step_response_velocity.npy',
                          'data/step_response_velocity.npy',
                          os.path.expanduser('~/tesis_black_robot/step_response_velocity.npy')]:
            if os.path.exists(candidate):
                npy_path = candidate
                break
        else:
            print(f"ERROR: No se encontró {npy_path}")
            print("Uso: python3 analizar_pid.py ruta/a/step_response_velocity.npy")
            sys.exit(1)

    print(f"\n{'═'*60}")
    print(f"  Analizando PID: {npy_path}")
    print(f"{'═'*60}")

    print("\n[1/6] Cargando datos...")
    t, y_izq, y_der = cargar_datos(npy_path)
    print(f"      {len(t)} muestras, dt≈{(t[-1]-t[0])/(len(t)-1):.4f} s, "
          f"duración={t[-1]-t[0]:.2f} s")

    print("[2/6] Calculando métricas PSO (datos reales)...")
    met_pso_izq = calcular_metricas(t, y_izq, REF_VEL)
    met_pso_der = calcular_metricas(t, y_der, REF_VEL)
    print(f"      IZQ: Mp={met_pso_izq['Mp']:.2f}%  tr={met_pso_izq['tr']:.3f}s  "
          f"ts={met_pso_izq['ts']:.3f}s  ess={met_pso_izq['ess']:.4f} m/s")
    print(f"      DER: Mp={met_pso_der['Mp']:.2f}%  tr={met_pso_der['tr']:.3f}s  "
          f"ts={met_pso_der['ts']:.3f}s  ess={met_pso_der['ess']:.4f} m/s")

    print("[3/6] Identificando modelo FODT (Differential Evolution)...")
    K_i, tau_i, L_i = identificar_fodt(t, y_izq, REF_VEL)
    K_d, tau_d, L_d = identificar_fodt(t, y_der, REF_VEL)
    print(f"      IZQ: K={K_i:.4f}  τ={tau_i:.4f} s  L={L_i:.4f} s")
    print(f"      DER: K={K_d:.4f}  τ={tau_d:.4f} s  L={L_d:.4f} s")

    print("[4/6] Calculando ganancias Lambda (λ=3τ)...")
    lam_i = lambda_tuning(K_i, tau_i, L_i, factor=3.0)
    lam_d = lambda_tuning(K_d, tau_d, L_d, factor=3.0)
    print(f"      IZQ Lambda: Kp={lam_i['Kp']:.4f}  Ki={lam_i['Ki']:.4f}  Kd={lam_i['Kd']:.4f}")
    print(f"      DER Lambda: Kp={lam_d['Kp']:.4f}  Ki={lam_d['Ki']:.4f}  Kd={lam_d['Kd']:.4f}")

    print("[5/6] Simulando lazo cerrado con ganancias Lambda...")
    t_sim = np.linspace(t[0], t[-1], max(len(t), 500))
    y_lam_izq = simular_pid_lc(t_sim, K_i, tau_i, L_i, lam_i['Kp'], lam_i['Ki'], lam_i['Kd'], REF_VEL)
    y_lam_der = simular_pid_lc(t_sim, K_d, tau_d, L_d, lam_d['Kp'], lam_d['Ki'], lam_d['Kd'], REF_VEL)
    met_lam_izq = calcular_metricas(t_sim, y_lam_izq, REF_VEL)
    met_lam_der = calcular_metricas(t_sim, y_lam_der, REF_VEL)

    print("[6/6] Generando salidas...")
    plot_escalon(t, y_izq, y_der,
                 K_i, tau_i, L_i, K_d, tau_d, L_d,
                 KP_IZQ, KI_IZQ, KD_IZQ, KP_DER, KI_DER, KD_DER,
                 os.path.join(OUTDIR, 'pid_escalon.png'))
    plot_pso_vs_lambda(t_sim, lam_i, lam_d,
                       K_i, tau_i, L_i, K_d, tau_d, L_d,
                       os.path.join(OUTDIR, 'pid_pso_vs_lambda.png'))
    guardar_csv(met_pso_izq, met_pso_der, lam_i, lam_d,
                met_lam_izq, met_lam_der,
                K_i, tau_i, L_i, K_d, tau_d, L_d,
                os.path.join(OUTDIR, 'pid_resultados.csv'))

    latex = generar_latex(K_i, tau_i, L_i, K_d, tau_d, L_d,
                          met_pso_izq, met_pso_der,
                          lam_i, lam_d, met_lam_izq, met_lam_der)
    tex_path = os.path.join(OUTDIR, 'pid_tablas.tex')
    with open(tex_path, 'w') as f:
        f.write(latex)
    print(f"  ✓ {tex_path}")

    print(f"\n{'═'*60}")
    print("  RESUMEN PARA LA TESIS")
    print(f"{'═'*60}")
    print(f"  Copiar imágenes a:  2.Texto/Imag/")
    print(f"    pid_escalon.png       → fig:respuesta_escalon_pso")
    print(f"    pid_pso_vs_lambda.png → fig:comparacion_pso_vs_lambda")
    print(f"  Incluir tablas de:  pid_tablas.tex")
    print(f"{'═'*60}\n")

if __name__ == '__main__':
    main()