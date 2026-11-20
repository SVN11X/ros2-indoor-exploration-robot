# 🤖 Tesis Black Robot - Guía de Acceso y Trabajo

Versión en inglés: [README.en.md](README.en.md)

Este documento detalla los pasos para instalar Git, clonar el repositorio y el flujo de trabajo para subir o bajar cambios.

---

## 🛠️ 1. Instalar Git

Si no tienes Git instalado:
* **🪟 Windows:** Descarga e instala desde [git-scm.com](https://git-scm.com/download/win).
* **🐧 Ubuntu:** Ejecuta `sudo apt update && sudo apt install git -y`.

---

## ⚙️ 2. Configurar tu Identidad

Git guarda tu nombre y correo en cada commit. Ejecuta esto una vez:

```bash
git config --global user.name "TuUsuarioGitHub"
git config --global user.email "tu_email@ejemplo.com"
```

---

## 🚀 3. Clonar el Repositorio (Primera vez)

El repositorio es público, así que clonarlo no pide credenciales. Instala antes Git LFS, porque los archivos grandes de las sesiones de mapeo están ahí. Los scripts esperan el repositorio en `~/tesis_black_robot`:

```bash
sudo apt install git-lfs
git lfs install
git clone https://github.com/SVN11X/ros2-indoor-exploration-robot.git ~/tesis_black_robot
```

---

## 🔄 4. Flujo de Trabajo Diario

Estos son los comandos que usarás cada vez que trabajes en el proyecto. Funcionan igual en Windows y Ubuntu.

### ⬇️ Paso A: Traer cambios nuevos (Git Pull)
**Antes de empezar a trabajar**, siempre descarga la última versión para evitar conflictos.

```bash
git pull
```
*Esto descargará los avances que hayan subido tus compañeros.*

### ⬆️ Paso B: Subir tus cambios (Git Push)
Cuando termines de programar y quieras guardar tu trabajo en la nube:

1.  **Revisar qué modificaste (Opcional):**
    ```bash
    git status
    ```
    *(Verás en rojo los archivos modificados).*

2.  **Preparar los archivos:**
    ```bash
    git add .
    ```
    *(El punto `.` agrega **todo** lo que modificaste).*

3.  **Guardar la versión (Commit):**
    ```bash
    git commit -m "Descripción breve de lo que hice"
    ```
    *(Ejemplo: `git commit -m "Arreglé el bug del sensor"`).*

4.  **Enviar a GitHub (Push):**
    ```bash
    git push
    ```

---
**Mantenedor:** [SVN11X]