# -*- coding: utf-8 -*-
"""
AnalisisEstabilidadPID.py

Analisis de estabilidad y desempeno de la ley PID ejecutada por
diff_controller.h (ROSArduinoBridge) sobre el modelo FOPDT identificado
para cada rueda. Usa solo datos documentados en la tesis:

  - Modelo FOPDT identificado y ganancias sugeridas por PSO (Tabla A4.4):
    Km [(m/s)/PWM], tau [s], Ld [s], Kp, Kd y Ki.
  - Ganancias definitivas (Tabla 4.4).
  - Periodo del PID: PID_INTERVAL = 1000/30 = 33 ms (division entera).
  - Resolucion N_e = 1980 ticks/vuelta, radio r = 0.0335 m (Tabla 4.1),
    K_o = 50.
  - Datos de odometria y exploracion (Tablas 5.1, 5.2 y 5.4) para los
    intervalos de confianza de la Tabla A8.3.

Modelo de lazo:
  * Planta FOPDT continua  tau v' = -v + Km u(t - Ld), con u constante
    durante cada periodo del PID (retenedor de orden cero).
  * El retardo se escribe como Ld = (d + delta) T, con d entero y
    0 <= delta < 1, y se discretiza de forma exacta (retardo fraccionario).
  * Como la identificacion cuantiza el retardo a int(Ld/T_cap) muestras,
    todo Ld < T_cap = 0.1 s produce el mismo ajuste y el valor que entrega
    el optimizador no tiene significado fisico. Por eso el analisis se hace
    en los dos extremos posibles: Ld = 0, que es el modelo efectivamente
    ajustado (n_d = 0) y el que usa la sintonia, y Ld = T_cap, que es la
    cota superior. El valor del optimizador se informa solo como referencia
    y queda entre ambos extremos, porque los margenes son monotonos en Ld.
  * Medicion del firmware: ticks contados en el ultimo periodo, es decir,
    la velocidad media del periodo anterior.
  * Ley ejecutada (sin truncamientos ni saturacion):
        du[k] = (Kp e[k] - Kd (y[k]-y[k-1]) + I[k-1]) / Ko
        I[k]  = I[k-1] + Ki e[k]
        u[k]  = u[k-1] + du[k]
    En z:  U = Cr(z) R - Cy(z) Y
        Cr(z) = (Kp/Ko) z/(z-1) + (Ki/Ko) z/(z-1)^2
        Cy(z) = Cr(z) + Kd/Ko

Salidas: polos de lazo cerrado, margenes de ganancia, fase y retardo,
sensibilidad maxima Ms, barridos de robustez, banda de insensibilidad por
truncamiento entero, respuesta simulada e intervalos de confianza de los
ensayos.

Uso: python3 AnalisisEstabilidadPID.py  (requiere numpy y scipy).
Ubicacion en el repositorio: firmware/pid_config/.
"""
import numpy as np
from scipy import stats

T = 0.033                      # periodo real del PID [s]
T_CAP = 0.1                    # periodo de captura de la identificacion [s]
NE = 1980.0                    # ticks/vuelta
R_RUEDA = 0.0335               # m
KO = 50.0
KAPPA_T = NE * T / (2 * np.pi * R_RUEDA)            # ticks por periodo para 1 m/s (33 ms)
KAPPA_FW = NE / (np.pi * 0.067 * 30)                # factor del firmware (30 Hz nominal)

RUEDAS = {
    "izquierda": dict(Km=0.000913, tau=0.3291, Ld=0.0001, Kp=16.00, Kd=20.30, Ki=0.075, db=2),
    "derecha":   dict(Km=0.000890, tau=0.3485, Ld=0.0692, Kp=16.42, Kd=20.05, Ki=0.001, db=1),
}
PSO_REPORTADO = {"izquierda": (12.48, 34.69, 0.00001), "derecha": (10.10, 36.70, 0.00001)}
ESCALA_KD = 25.0               # cota superior evaluada por costFunction_PID()
GANANCIAS_ORIGINALES = (20.0, 12.0, 0.0)   # Kp, Kd, Ki por defecto del firmware original (ANEXO 4.5)
RETARDOS = [("sin retardo, Ld = 0 (modelo efectivo, n_d = 0)", 0.0), ("Ld = T_cap (cota superior)", T_CAP)]


# ---------------------------------------------------------------- planta
def planta(Km, tau, Ld, T=T, kappa=KAPPA_T):
    """FOPDT discreta desde el PWM hasta la medicion (ticks por periodo).

    Ld = (d + delta) T.  P(z) = K N(z) / (z^(d+2) (z - a)), con
        a = exp(-T/tau), gamma = tau (1 - a) / T, a_d = a^(1 - delta),
        c_n = (1 - delta) - (tau/T)(1 - a_d),  c_o = delta - (tau/T)(a_d - a),
        N(z) = (c_n z + c_o)(z - a) + gamma [(1 - a_d) z + a_d - a].
    Con Ld = 0 se reduce a K[(1-gamma) z + gamma - a] / [z (z - a)].
    """
    K = Km * kappa
    a = np.exp(-T / tau)
    g = tau * (1 - a) / T
    q = Ld / T
    d = int(np.floor(q + 1e-12))
    de = q - d
    ad = a ** (1 - de)
    c_n = (1 - de) - (tau / T) * (1 - ad)
    c_o = de - (tau / T) * (ad - a)
    N = np.polyadd(np.polymul([c_n, c_o], [1.0, -a]), g * np.array([1 - ad, ad - a]))
    num = K * N
    den = np.polymul([1.0, -a], np.r_[1.0, np.zeros(d + 2)])
    return num, den, dict(K=K, a=a, gamma=g, d=d, delta=de, a_d=ad, c_n=c_n, c_o=c_o)


def controlador_y(Kp, Kd, Ki, Ko=KO):
    """Cy(z) = Cr(z) + Kd/Ko, con Cr(z) = (Kp/Ko) z/(z-1) + (Ki/Ko) z/(z-1)^2."""
    kI, kP, kII = Kp / Ko, Kd / Ko, Ki / Ko
    if kII == 0.0:
        num = np.array([kI + kP, -kP])
        den = np.array([1.0, -1.0])
    else:
        num = kI * np.array([1.0, -1.0, 0.0]) + kP * np.array([1.0, -2.0, 1.0]) + kII * np.array([0.0, 1.0, 0.0])
        den = np.array([1.0, -2.0, 1.0])
    return num, den


def polos_lazo_cerrado(numP, denP, numC, denC, retardo=0):
    numL = np.polymul(numP, numC)
    denL = np.polymul(np.polymul(denP, denC), np.r_[1.0, np.zeros(retardo)])
    car = np.polyadd(denL, numL)
    return np.roots(car)


def estable(numP, denP, numC, denC, retardo=0):
    return np.max(np.abs(polos_lazo_cerrado(numP, denP, numC, denC, retardo))) < 1.0


def respuesta_frecuencia(numP, denP, numC, denC, n=200000):
    w = np.linspace(1e-3, np.pi / T * 0.9999, n)
    z = np.exp(1j * w * T)
    L = np.polyval(numP, z) / np.polyval(denP, z) * np.polyval(numC, z) / np.polyval(denC, z)
    return w, L


def margenes(w, L):
    mag = np.abs(L)
    fase = np.unwrap(np.angle(L))
    idx = np.where((mag[:-1] >= 1) & (mag[1:] < 1))[0]
    wc = pm = dm = np.nan
    if idx.size:
        i = idx[0]
        wc = np.interp(1.0, [mag[i + 1], mag[i]], [w[i + 1], w[i]])
        fc = np.interp(wc, w, fase)
        pm = np.degrees(np.pi + fc)
        dm = np.radians(pm) / wc
    idx2 = np.where((fase[:-1] > -np.pi) & (fase[1:] <= -np.pi))[0]
    gm = w180 = np.nan
    if idx2.size:
        i = idx2[0]
        w180 = np.interp(-np.pi, [fase[i + 1], fase[i]], [w[i + 1], w[i]])
        gm = 1.0 / np.interp(w180, w, mag)
    Ms = np.max(np.abs(1.0 / (1.0 + L)))
    return dict(wc=wc, pm=pm, dm=dm, w180=w180, gm=gm, gm_db=20 * np.log10(gm), Ms=Ms)


def max_retardo_entero(numP, denP, numC, denC, dmax=200):
    for d in range(0, dmax):
        if not estable(numP, denP, numC, denC, d):
            return d - 1
    return dmax


def retardo_critico(Km, tau, numC, denC, Ld0, paso=0.0005, Lmax=2.0):
    """Mayor retardo total Ld (s) con lazo estable, barriendo desde Ld0."""
    L = Ld0
    while L < Lmax:
        numP, denP, _ = planta(Km, tau, L + paso)
        if not estable(numP, denP, numC, denC):
            return L
        L += paso
    return Lmax


# -------------------------------------------------- simulacion bit-exacta
def escalon_firmware(Km, tau, Ld, Kp, Kd, Ki, db, ref_mps=0.13, tf=10.0, zona_muerta=0.0):
    """Replica de doPID(): enteros, truncamiento hacia cero, banda muerta,
    saturacion e integracion condicional. La planta FOPDT recibe el PWM
    entero con el retardo Ld."""
    sub = 20
    dt = T / sub
    nret = int(round(Ld / dt))
    N = int(tf / T)
    hist = [0.0] * (nret + 1)
    v = 0.0; pos = 0.0; cnt_prev = 0
    output = 0; prev_input = 0; ITerm = 0
    target = ref_mps * KAPPA_FW
    ys = []
    for k in range(N):
        if abs(output) > zona_muerta:
            u_ef = np.sign(output) * (abs(output) - zona_muerta) * 255.0 / (255.0 - zona_muerta)
        else:
            u_ef = 0.0
        for _ in range(sub):
            hist.append(u_ef)
            u_ret = hist.pop(0)
            v = v + dt / tau * (Km * u_ret - v)
            pos += v * dt * NE / (2 * np.pi * R_RUEDA)
        cnt = int(np.floor(pos))
        inp = cnt - cnt_prev
        cnt_prev = cnt
        perr = int(target - inp)
        if abs(perr) <= db:
            perr = 0
        inc = int((Kp * perr - Kd * (inp - prev_input) + ITerm) / KO)
        out = inc + output
        if out >= 255:
            out = 255
        elif out <= -255:
            out = -255
        else:
            ITerm = int(ITerm + Ki * perr)
        output = out
        prev_input = inp
        ys.append(inp)
    t = np.arange(1, N + 1) * T
    return t, np.array(ys) / KAPPA_FW


def indicadores(t, y, ref):
    yss = np.mean(y[t >= 7.0])
    try:
        t10 = t[np.where(y >= 0.1 * ref)[0][0]]
        t90 = t[np.where(y >= 0.9 * ref)[0][0]]
        tr = t90 - t10
    except IndexError:
        tr = np.nan
    os_ = max(0.0, (np.max(y) - ref) / ref * 100)
    return yss, tr, os_


def banda_truncamiento(Kp, I=0.0):
    """Mayor error entero que no modifica la salida: Kp*e + I < Ko."""
    e = 0
    while int((Kp * (e + 1) + I) / KO) == 0:
        e += 1
    return e


# ------------------------------------- reproduccion del simulador del PSO
def simular_como_pso(pid, Km, tau, deadband=2, tf=10.0, ts_cap=0.1, t_escalon=1.0, pwm=143):
    """Replica simular_pid_firmware() de SintonizacionAutomatica.py: punto
    flotante, medicion instantanea redondeada, Euler con 1/30 s, sin aplicar
    el retardo (la variable delay_steps no se usa) y referencia escalon igual
    a la velocidad estacionaria del modelo (Km*143)."""
    kp, kd, ki = pid
    t = np.arange(0, tf + ts_cap, ts_cap)
    vss = Km * pwm
    cv = np.zeros_like(t); cv[t >= t_escalon] = vss
    ts = 1.0 / 30
    t_sim = np.arange(t[0], t[-1] + ts, ts); N = len(t_sim)
    pv = np.zeros(N); out = 0.0; I = 0.0; prev = 0
    for k in range(1, N):
        sp = float(np.interp(t_sim[k], t, cv))
        pv[k] = max(0.0, pv[k-1] + (ts / tau) * (Km * out - pv[k-1]))
        tt = sp * KAPPA_FW; ci = int(round(pv[k] * KAPPA_FW)); e = tt - ci
        if abs(e) <= deadband:
            e = 0
        out += (kp * e - kd * (ci - prev) + I) / KO
        if out >= 255: out = 255.0
        elif out <= -255: out = -255.0
        else: I += ki * e
        prev = ci
    r = np.interp(t, t_sim, pv)
    i10 = np.where(r >= 0.1 * vss)[0][0]; i90 = np.where(r >= 0.9 * vss)[0][0]
    os_ = max(0.0, (r.max() - vss) / vss * 100)
    return vss, np.mean(r[t >= 7.0]), t[i90] - t[i10], os_


def costo_identificacion_constante(Km, tau, dt=T_CAP, N=101, pwm=143.0):
    """Muestra que fodt() de los scripts entrega la misma respuesta para todo
    Ld < T_cap: el retardo se cuantiza como int(Ld/dt) muestras."""
    cv = np.zeros(N); cv[10:] = pwm
    def fodt(delay):
        pv = np.zeros(N)
        for k in range(1, N):
            steps = int(delay / dt)
            u = cv[max(k - steps, 0)]
            pv[k] = pv[k-1] + (dt / tau) * (Km * u - pv[k-1])
        return pv
    ref = fodt(0.0)
    return {L: float(np.max(np.abs(fodt(L) - ref))) for L in [0.0001, 0.0692, 0.0845, 0.099, 0.1]}


def verificar_discretizacion(Km, tau, Ld, nper=40, sub=2000):
    """Compara la respuesta de P(z) a un pulso unitario de PWM con la del
    modelo FOPDT continuo simulado con un paso fino (T/sub)."""
    from scipy.signal import dimpulse, dlti
    numP, denP, _ = planta(Km, tau, Ld)
    _, h = dimpulse(dlti(numP, denP, dt=T), n=nper + 1)
    h = np.squeeze(h)
    dt = T / sub
    v = 0.0
    m = np.zeros(nper)
    for i in range(nper * sub):
        ti = i * dt - Ld
        u = 1.0 if 0.0 <= ti < T else 0.0
        v += dt / tau * (Km * u - v)
        m[i // sub] += v * dt * KAPPA_T / T
    return float(np.max(np.abs(h[1:nper + 1] - m)))


def margenes_caso(p, Ld, Kp, Kd, Ki):
    """Margenes y mayor magnitud de polos para una rueda, un retardo y unas ganancias."""
    numP, denP, _ = planta(p["Km"], p["tau"], Ld)
    numC, denC = controlador_y(Kp, Kd, Ki)
    w, L = respuesta_frecuencia(numP, denP, numC, denC)
    m = margenes(w, L)
    m["polo"] = np.max(np.abs(polos_lazo_cerrado(numP, denP, numC, denC)))
    return m


def barrido_retardo(p, Kp, Kd, Ki, n=11):
    """Margenes para Ld entre 0 y T_cap. Indica si varian de forma monotona."""
    filas = [(Ld, margenes_caso(p, Ld, Kp, Kd, Ki)) for Ld in np.linspace(0.0, T_CAP, n)]
    pm = np.array([m["pm"] for _, m in filas])
    gm = np.array([m["gm_db"] for _, m in filas])
    dm = np.array([m["dm"] for _, m in filas])
    ms = np.array([m["Ms"] for _, m in filas])
    monot = bool(np.all(np.diff(pm) < 0) and np.all(np.diff(gm) < 0)
                 and np.all(np.diff(dm) < 0) and np.all(np.diff(ms) > 0))
    return filas, monot


def ganancia_critica(p, Ld, numC, denC, tau=None, lo=0.1, hi=500.0):
    """Menor multiplicador de Km que vuelve inestable el lazo (biseccion)."""
    tau = p["tau"] if tau is None else tau
    numP, denP, _ = planta(p["Km"] * hi, tau, Ld)
    if estable(numP, denP, numC, denC):
        return np.inf
    numP, denP, _ = planta(p["Km"] * lo, tau, Ld)
    if not estable(numP, denP, numC, denC):
        return lo
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        numP, denP, _ = planta(p["Km"] * mid, tau, Ld)
        if estable(numP, denP, numC, denC):
            lo = mid
        else:
            hi = mid
    return lo


# ---------------------------------------------------------------- informe
def informe_lazo(etiqueta, p, Ld, Kp, Kd, Ki):
    numP, denP, info = planta(p["Km"], p["tau"], Ld)
    numC, denC = controlador_y(Kp, Kd, Ki)
    pol = polos_lazo_cerrado(numP, denP, numC, denC)
    w, L = respuesta_frecuencia(numP, denP, numC, denC)
    m = margenes(w, L)
    dext = max_retardo_entero(numP, denP, numC, denC)
    Lcrit = retardo_critico(p["Km"], p["tau"], numC, denC, Ld)
    print(f"  [{etiqueta}] Ld = {Ld:.4f} s (d = {info['d']}, delta = {info['delta']:.3f})")
    print(f"    polos dominantes |max| = {np.max(np.abs(pol)):.4f}; "
          f"polos: {np.round(pol[np.argsort(-np.abs(pol))][:4], 4)}")
    print(f"    wc = {m['wc']:.3f} rad/s, T*wc = {T*m['wc']:.4f}, PM = {m['pm']:.1f} deg, "
          f"DM = {m['dm']:.3f} s, w180 = {m['w180']:.2f} rad/s, GM = {m['gm']:.1f} ({m['gm_db']:.1f} dB), Ms = {m['Ms']:.4f}")
    print(f"    retardo entero adicional maximo estable: {dext} periodos ({dext*T:.3f} s); "
          f"retardo total critico = {Lcrit:.3f} s")
    return m, info


def main():
    np.set_printoptions(precision=4, suppress=True)
    print(f"kappa_T (33 ms) = {KAPPA_T:.2f} ticks por periodo para 1 m/s; kappa_fw = {KAPPA_FW:.2f}")
    print("\n===== Identificacion: el costo no cambia para Ld < T_cap =====")
    for nombre, p in RUEDAS.items():
        dif = costo_identificacion_constante(p["Km"], p["tau"])
        print(f"  {nombre}: max |respuesta(Ld) - respuesta(0)| = " +
              ", ".join(f"Ld={k:.4f}: {v:.2e}" for k, v in dif.items()))
    print("\n===== Verificacion de la discretizacion FOPDT (pulso unitario de PWM) =====")
    for nombre, p in RUEDAS.items():
        for Ld in [p["Ld"], T_CAP]:
            err = verificar_discretizacion(p["Km"], p["tau"], Ld)
            print(f"  {nombre}, Ld = {Ld:.4f} s: max |P(z) - modelo continuo| = {err:.2e} ticks por periodo")
    for nombre, p in RUEDAS.items():
        print(f"\n===== Rueda {nombre} =====")
        _, _, info = planta(p["Km"], p["tau"], p["Ld"])
        print(f"K = {info['K']:.4f} (ticks por periodo)/PWM, a = {info['a']:.5f}, gamma = {info['gamma']:.5f}, "
              f"retardo relativo Ld/(Ld+tau) = {p['Ld']/(p['Ld']+p['tau']):.3f} (cota {T_CAP/(T_CAP+p['tau']):.3f})")
        kc, ti = p["Kd"] / KO, p["Kd"] / p["Kp"] * T
        print(f"PI incremental equivalente: K = Kd/Ko = {kc:.4f} PWM por tick/frame, "
              f"K h/Ti = Kp/Ko = {p['Kp']/KO:.4f}, Ti = {ti*1000:.1f} ms")
        for etiqueta_r, Ld in RETARDOS:
            informe_lazo(f"definitivas, {etiqueta_r}", p, Ld, p["Kp"], p["Kd"], 0.0)
            if nombre == "izquierda":
                informe_lazo(f"definitivas, {etiqueta_r}, Ki lineal", p, Ld, p["Kp"], p["Kd"], p["Ki"])
        informe_lazo("definitivas, Ld del optimizador (solo referencia)", p, p["Ld"], p["Kp"], p["Kd"], 0.0)
        casos = [("definitivas", p["Kp"], p["Kd"], 0.0)]
        if nombre == "izquierda":
            casos.append(("definitivas, Ki lineal", p["Kp"], p["Kd"], p["Ki"]))
        for etiqueta, kp_, kd_, ki_ in casos:
            filas, monot = barrido_retardo(p, kp_, kd_, ki_)
            print(f"  barrido de Ld entre 0 y T_cap ({etiqueta}): margenes monotonos = {monot}")
            for Ld, m in filas:
                print(f"    Ld = {Ld:.3f} s: PM = {m['pm']:.1f} deg, GM = {m['gm_db']:.1f} dB, "
                      f"DM = {m['dm']:.3f} s, Ms = {m['Ms']:.3f}, polo |max| = {m['polo']:.4f}")
        kp, kd_rep, ki = PSO_REPORTADO[nombre]
        for etiqueta, kd in [("PSO evaluado (Kd=25)", ESCALA_KD), ("PSO informado", kd_rep)]:
            for etiqueta_r, Ld in RETARDOS:
                informe_lazo(f"{etiqueta}, {etiqueta_r}", p, Ld, kp, kd, 0.0)
        for etiqueta_r, Ld in RETARDOS:
            informe_lazo(f"ganancias por defecto del firmware original (Kp=20, Kd=12, Ki=0), {etiqueta_r}",
                         p, Ld, *GANANCIAS_ORIGINALES)
        for etiqueta, kp_ in [("final", p["Kp"]), ("PSO", PSO_REPORTADO[nombre][0])]:
            e = banda_truncamiento(kp_)
            print(f"  banda de insensibilidad ({etiqueta}, Kp={kp_}): |e| <= {e} ticks/frame = {e/KAPPA_FW:.4f} m/s")
        print(f"  error para que Ki*e alcance una unidad: {1/p['Ki']:.1f} ticks/frame")
        for zm in [0.0, 40.0]:
            t, y = escalon_firmware(p["Km"], p["tau"], 0.0, p["Kp"], p["Kd"], p["Ki"], p["db"], zona_muerta=zm)
            yss, tr, os_ = indicadores(t, y, 0.13)
            print(f"  firmware bit-exacto, definitivas, sin retardo (zona muerta {zm:.0f} PWM): yss={yss:.4f}, tr={tr:.2f} s, OS={os_:.1f}%")

    print("\n===== Prediccion con la rutina de simulacion del PSO (sin retardo aplicado) =====")
    for nombre, p in RUEDAS.items():
        kp, kd_rep, ki = PSO_REPORTADO[nombre]
        for etiqueta, g in [("PSO evaluado (Kd=25)", (kp, ESCALA_KD, ki)),
                            ("PSO informado", (kp, kd_rep, ki)),
                            ("definitivas", (p["Kp"], p["Kd"], p["Ki"]))]:
            vss, yss, tr, os_ = simular_como_pso(g, p["Km"], p["tau"])
            print(f"  {nombre}, {etiqueta}: referencia {vss:.4f} m/s, yss={yss:.4f}, tr={tr:.2f} s, OS={os_:.1f}%")

    print("\n===== Barrido de robustez (625 combinaciones) =====")
    mult = np.logspace(-1, 1, 25)
    taus = np.linspace(0.05, 3.0, 25)
    for nombre, p in RUEDAS.items():
        casos = [("", 0.0)]
        if nombre == "izquierda":
            casos.append((", Ki lineal", p["Ki"]))
        for etiqueta_k, ki_ in casos:
            numC, denC = controlador_y(p["Kp"], p["Kd"], ki_)
            for etiqueta, Ld in [("sin retardo", 0.0), ("Ld del optimizador", p["Ld"]), ("Ld = T_cap", T_CAP)]:
                inest = []
                for m_ in mult:
                    for ta in taus:
                        numP, denP, _ = planta(p["Km"] * m_, ta, Ld)
                        if not estable(numP, denP, numC, denC):
                            inest.append(m_)
                kcrit = ganancia_critica(p, Ld, numC, denC)
                kmin = min(ganancia_critica(p, Ld, numC, denC, tau=ta) for ta in taus)
                extra = f"; menor multiplicador inestable en la grilla = {min(inest):.2f}" if inest else ""
                print(f"  {nombre}{etiqueta_k}, {etiqueta} (Ld = {Ld:.4f} s): inestables {len(inest)}/625; "
                      f"ganancia critica con tau nominal = {kcrit:.2f} x Km; "
                      f"minima en el rango de tau = {kmin:.2f} x Km{extra}")

    print("\n===== Condiciones de operacion =====")
    v_max, w_max, b_sep = 0.13, 0.35, 0.188
    vr = v_max + w_max * b_sep / 2
    print(f"  velocidad maxima de rueda = {vr:.4f} m/s = {vr*KAPPA_FW:.1f} ticks/frame")
    for nombre, p in RUEDAS.items():
        print(f"  PWM estacionario requerido ({nombre}) = {vr/p['Km']:.0f}")
    print(f"  giro en el lugar a 0.35 rad/s: rueda = {w_max*b_sep/2:.4f} m/s = {w_max*b_sep/2*KAPPA_FW:.1f} ticks/frame")
    print(f"  paso maximo de consigna Nav2 por ciclo (8 Hz): lineal {0.25/8:.4f} m/s")

    print("\n===== Intervalos de confianza (95 %) =====")
    def ic(x, nombre):
        x = np.asarray(x, float); n = x.size
        mu, s = x.mean(), x.std(ddof=1)
        h = stats.t.ppf(0.975, n - 1) * s / np.sqrt(n)
        print(f"  {nombre}: n={n}, media={mu:.4f}, s={s:.4f}, IC95=[{mu-h:.4f}, {mu+h:.4f}] (semiamplitud {h:.4f})")
        return mu, s, h
    e_odom = [4.01, 2.88, 3.87, 3.78, 3.61]
    d_real = [1.846, 1.868, 1.851, 1.856, 1.861]
    e_seg = [abs(d - 2.0) / 2.0 * 100 for d in d_real]
    giro = [355.7, 340.0, 380.0, 370.0, 356.0]
    dev_giro = [abs(g - 360) for g in giro]
    cobertura = [82.9, 53.5, 54.2, 67.1, 53.4]
    area = [3.510, 3.540, 3.478, 3.483, 3.478]
    dur = [3.45, 2.16, 2.27, 2.50, 2.30]
    dist = [6.305, 3.536, 4.144, 3.850, 4.066]
    ic(e_odom, "E_odom (%)")
    ic(e_seg, "E_seg real (%)")
    ic(dev_giro, "desviacion angular |dtheta-360| real (grados)")
    ic(cobertura, "cobertura libre (%)")
    ic(area, "area libre (m2)")
    vel = [d / (m * 60) for d, m in zip(dist, dur)]
    ic(vel, "rapidez media de recorrido en exploracion (m/s)")
    print(f"  recorrido total = {sum(dist):.3f} m en {sum(dur):.2f} min")
    print(f"  CV area libre = {np.std(area, ddof=1)/np.mean(area)*100:.2f} %")
    lo = stats.beta.ppf(0.025, 5, 6 - 5 + 1); hi = stats.beta.ppf(0.975, 5 + 1, 6 - 5)
    print(f"  exploraciones validas 5/6: IC95 exacto (Clopper-Pearson) = [{lo*100:.1f}, {hi*100:.1f}] %")
    s = np.std(e_odom, ddof=1)
    h5 = stats.t.ppf(0.975, 4) * s / np.sqrt(5)
    for n in range(5, 60):
        if stats.t.ppf(0.975, n - 1) * s / np.sqrt(n) <= h5 / 2:
            print(f"  repeticiones para reducir a la mitad la semiamplitud de E_odom: n = {n}")
            break
    for n in range(6, 200):
        if stats.beta.ppf(0.025, n, 1) >= 0.80:
            print(f"  ensayos sin fallas necesarios para que el limite inferior del IC95 supere 80 %: n = {n}")
            break
    print(f"  15 exitos en 15 intentos: limite inferior IC95 = {stats.beta.ppf(0.025, 15, 1)*100:.1f} %")


if __name__ == "__main__":
    main()
