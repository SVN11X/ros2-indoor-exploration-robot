# Guía de Instalación: Entorno de Desarrollo en Ubuntu 20.04

Versión en inglés: [README.en.md](README.en.md)

A continuación se detallan los métodos por terminal y manuales para configurar Git, Visual Studio Code, Microsoft Edge y Arduino IDE.

## 1. Sistema Base y Git
Actualización de repositorios e instalación del sistema de control de versiones.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install git -y
```

---

## 2. Visual Studio Code
El editor de código principal. Puedes elegir instalarlo vía Snap (terminal) o descargando el paquete oficial (manual).

### Opción A: Terminal (Snap)
Es el método más rápido y se actualiza automáticamente.

```bash
sudo snap install --classic code
```

### Opción B: Manual (Paquete .deb)
1. Ir al sitio oficial: [code.visualstudio.com](https://code.visualstudio.com/).
2. Descargar el archivo **.deb** (para Debian/Ubuntu).
3. Abrir la carpeta de Descargas, hacer clic derecho sobre el archivo descargado y seleccionar **"Abrir con Instalación de Software"**.
4. Clic en "Instalar".

### Instalación de Extensiones (Vía Terminal)
Una vez instalado Visual Studio Code, ejecuta el siguiente comando para instalar el "Remote Development Pack" (que incluye SSH, WSL y Dev Containers) automáticamente sin abrir la interfaz gráfica:

```bash
# Instalar Remote Development Extension Pack
code --install-extension ms-vscode-remote.vscode-remote-extensionpack
```

---

## 3. Microsoft Edge
Navegador basado en Chromium. No viene en los repositorios por defecto.

### Opción A: Terminal (Línea de comandos)
Descarga e instala la versión estable directamente.

```bash
# 1. Descargar el paquete más reciente
wget https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_128.0.2739.67-1_amd64.deb -O edge.deb

# 2. Instalar el paquete
sudo apt install ./edge.deb -y

# 3. Eliminar archivo temporal
rm edge.deb
```

### Opción B: Manual (Web)
1. Ir al sitio oficial: [microsoft.com/edge](https://www.microsoft.com/edge).
2. Seleccionar "Descargar para Linux" (.deb).
3. Aceptar los términos y guardar el archivo.
4. Una vez descargado, doble clic sobre el archivo `.deb` para abrir el instalador de software de Ubuntu y presionar **"Instalar"**.

---

## 4. Arduino IDE
Entorno para desarrollo de hardware.

### Opción A: Terminal (Snap)
Versión mantenida en la tienda de aplicaciones de Canonical.

```bash
sudo snap install arduino
```

### Opción B: Manual (AppImage / Zip)
Recomendado si necesitas una versión específica (Legacy 1.8 o la nueva 2.x) que no está en Snap.

1. Ir a [arduino.cc/en/software](https://www.arduino.cc/en/software).
2. Descargar la opción **"Linux AppImage 64 bits"** (para la versión 2.x).
3. Clic derecho en el archivo descargado -> **Propiedades** -> Pestaña **Permisos**.
4. Marcar la casilla **"Permitir ejecutar el archivo como un programa"**.
5. Doble clic para abrir.

### Asignación de permisos (Obligatorio para ambos métodos)
Independiente de cómo lo instales, debes añadir tu usuario al grupo `dialout` para poder subir código a la placa mediante USB.

```bash
sudo usermod -a -G dialout $USER
```

> **Requerimiento:** Es necesario reiniciar el sistema o cerrar y volver a iniciar sesión para que los cambios en los permisos de usuario (Arduino) se apliquen correctamente.