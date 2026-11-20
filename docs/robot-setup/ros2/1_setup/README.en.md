# Installation Guide: Development Environment on Ubuntu 20.04

Spanish version: [README.md](README.md)

Terminal and manual methods to set up Git, Visual Studio Code, Microsoft Edge and the Arduino IDE.

## 1. Base System and Git
Update the package lists and install the version control system.

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install git -y
```

---

## 2. Visual Studio Code
The main code editor. You can install it with Snap (terminal) or by downloading the official package (manual).

### Option A: Terminal (Snap)
The fastest method, and it updates automatically.

```bash
sudo snap install --classic code
```

### Option B: Manual (.deb package)
1. Go to the official site: [code.visualstudio.com](https://code.visualstudio.com/).
2. Download the **.deb** file (for Debian/Ubuntu).
3. Open the Downloads folder, right-click the downloaded file and select **"Open with Software Install"**.
4. Click "Install".

### Installing Extensions (Terminal)
Once Visual Studio Code is installed, run the following command to install the "Remote Development Pack" (which includes SSH, WSL and Dev Containers) without opening the graphical interface:

```bash
# Instalar Remote Development Extension Pack
code --install-extension ms-vscode-remote.vscode-remote-extensionpack
```

---

## 3. Microsoft Edge
A Chromium-based browser. It is not in the default repositories.

### Option A: Terminal (Command line)
Download and install the stable version directly.

```bash
# 1. Descargar el paquete más reciente
wget https://packages.microsoft.com/repos/edge/pool/main/m/microsoft-edge-stable/microsoft-edge-stable_128.0.2739.67-1_amd64.deb -O edge.deb

# 2. Instalar el paquete
sudo apt install ./edge.deb -y

# 3. Eliminar archivo temporal
rm edge.deb
```

### Option B: Manual (Web)
1. Go to the official site: [microsoft.com/edge](https://www.microsoft.com/edge).
2. Select "Download for Linux" (.deb).
3. Accept the terms and save the file.
4. Once downloaded, double-click the `.deb` file to open the Ubuntu software installer and press **"Install"**.

---

## 4. Arduino IDE
Environment for hardware development.

### Option A: Terminal (Snap)
Version maintained in the Canonical app store.

```bash
sudo snap install arduino
```

### Option B: Manual (AppImage / Zip)
Recommended if you need a specific version (Legacy 1.8 or the new 2.x) that is not in Snap.

1. Go to [arduino.cc/en/software](https://www.arduino.cc/en/software).
2. Download the **"Linux AppImage 64 bits"** option (for version 2.x).
3. Right-click the downloaded file -> **Properties** -> **Permissions** tab.
4. Check the box **"Allow executing file as program"**.
5. Double-click to open it.

### Permissions (Required for both methods)
However you install it, you must add your user to the `dialout` group to upload code to the board over USB.

```bash
sudo usermod -a -G dialout $USER
```

> **Requirement:** Restart the system, or log out and log back in, so the user permission changes (Arduino) take effect.
