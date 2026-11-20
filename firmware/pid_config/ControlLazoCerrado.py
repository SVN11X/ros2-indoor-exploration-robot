from pyArduino import *
import numpy as np
import time
import matplotlib.pyplot as plt
import os

# --- CONFIGURACIÓN DE LA PRUEBA ---
port = 'COM4'           # Ajusta tu puerto
baudRate = 57600
ts = 0.1                # Tiempo de muestreo
tf = 10.0                # Duración de la prueba

# Velocidad objetivo (m/s)
target_velocity_mps = 0.13  

# -----------------------------------------------------

t = np.arange(0, tf+ts, ts)
N = len(t)
cv = np.zeros((N, 2))  
pv = np.zeros((N, 2))  

arduino = serialArduino(port, baudRate, sizeData=2)
arduino.readSerialStart()
time.sleep(2) 

print(f"\n--- PREPARANDO PRUEBA DE ESCALÓN ---")
print(f"Objetivo: {target_velocity_mps} m/s")

# # ==============================================================================
# #  BLOQUE INTERACTIVO: PREGUNTA AL USUARIO SOBRE EL PID
# # ==============================================================================
# print("\n¿Deseas sobreescribir los PIDs con valores suaves para identificación?")
# print("   (Esto pondrá Kp=15, Kd=0, Ki=0 para evitar oscilaciones)")
# respuesta = input(">> Escribe 's' para SI, o presiona ENTER para mantener los actuales: ").lower().strip()

# if respuesta == 's':
#     print("\n--> Configurando PID suave (Kp=15, Kd=0, Ki=0)...")
#     # Construimos el comando 'z' para ambas ruedas
#     # Formato: z KpL:KdL:KiL:KoL:KpR:KdR:KiR:KoR
#     kp_test = 15
#     ko_test = 50
#     cmd_str = f"z {kp_test}:0:0:{ko_test}:{kp_test}:0:0:{ko_test}\r"
    
#     # Enviamos comando directo al puerto serie
#     arduino.serialConnection.write(cmd_str.encode())
#     time.sleep(0.5) # Damos tiempo al Arduino para procesar
#     print("--> ¡PIDs actualizados temporalmente!")
# else:
#     print("\n--> OMITIDO. Se usarán los PIDs que ya tiene el Arduino en memoria.")

# ==============================================================================

# 1. Asegurar estado inicial detenido
arduino.sendData([0, 0], cmd='k') 
time.sleep(1)

print("\nIniciando movimiento en 3, 2, 1...")
time.sleep(1)

try:
    for k in range(N):
        start_time = time.time()

        # --- A. Generar Escalón en t=1.0s ---
        if t[k] >= 1.0:
            val_send = target_velocity_mps
        else:
            val_send = 0.0
        
        cv[k] = [val_send, val_send] 
        
        # --- B. Enviar Comando ---
        arduino.sendData([val_send, val_send], cmd='k')
        
        # --- C. Leer Velocidad ---
        arduino.sendData([], cmd='j') 
        
        # Leer respuesta
        if len(arduino.rawData) >= 2:
             pv[k] = np.array(arduino.rawData)
        else:
             pv[k] = [0.0, 0.0]

        # Monitoreo en consola cada 5 muestras
        if k % 5 == 0:
            print(f"T={t[k]:.1f}s | Ref: {val_send:.2f} | L: {pv[k,0]} | R: {pv[k,1]}")

        # Control de tiempo exacto
        elapsed = time.time() - start_time
        sleep_time = ts - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

except KeyboardInterrupt:
    print("\nInterrupción por usuario.")

finally:
    print("\nDeteniendo robot...")
    arduino.sendData([0, 0], cmd='k')
    time.sleep(0.5)
    arduino.close()
    
    # Guardar
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "step_response_velocity.npy")
    print(f"Datos guardados en: {file_path}")

    with open(file_path, 'wb') as f:
        np.save(f, cv) 
        np.save(f, pv) 
        np.save(f, t)  
        np.save(f, ts) 

    # --- GRAFICAR POR SEPARADO ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    
    fig.suptitle(f"Respuesta al escalón ({target_velocity_mps} m/s)", 
                 fontsize=13, fontweight='bold', y=0.97)

    # Gráfica Rueda Izquierda
    ax1.plot(t, cv[:,0], 'k--', label='Setpoint', alpha=0.7)
    ax1.plot(t, pv[:,0], 'r', label='Izquierda (medida)', linewidth=1.5)
    ax1.set_ylabel("Velocidad (m/s)")
    ax1.set_title("Rueda izquierda", fontsize=11, pad=6)
    ax1.legend(loc='lower right', fontsize=9)
    ax1.grid(True, alpha=0.3)

    # Gráfica Rueda Derecha
    ax2.plot(t, cv[:,1], 'k--', label='Setpoint', alpha=0.7)
    ax2.plot(t, pv[:,1], 'b', label='Derecha (medida)', linewidth=1.5)
    ax2.set_xlabel("Tiempo (s)")
    ax2.set_ylabel("Velocidad (m/s)")
    ax2.set_title("Rueda derecha", fontsize=11, pad=6)
    ax2.legend(loc='lower right', fontsize=9)
    ax2.grid(True, alpha=0.3)

    plt.subplots_adjust(top=0.91, bottom=0.08, hspace=0.28)

    # Guardar figura
    fig_path = os.path.join(script_dir, "respuesta_escalon_final.png")
    plt.savefig(fig_path, dpi=150, bbox_inches='tight')
    print(f"Figura guardada en: {fig_path}")
    plt.show()