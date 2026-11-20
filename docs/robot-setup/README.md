# 🤖 Tesis Black Robot - Guía de Acceso y Trabajo

Versión en inglés: [README.en.md](README.en.md)

Este documento detalla los pasos para configurar las credenciales, clonar el repositorio privado y el flujo de trabajo para subir o bajar cambios.

> 🔒 **IMPORTANTE:** Al ser un repositorio privado, tu contraseña habitual de GitHub **NO funcionará**. Debes usar un **Personal Access Token**.

---

## 🛠️ 1. Instalar Git

Si no tienes Git instalado:
* **🪟 Windows:** Descarga e instala desde [git-scm.com](https://git-scm.com/download/win).
* **🐧 Ubuntu:** Ejecuta `sudo apt update && sudo apt install git -y`.

---

## 🔑 2. Generar tu Token de Acceso (Obligatorio)

Necesitas una "contraseña especial" para la terminal:

1.  Entra a tu cuenta de GitHub > **Settings** > **Developer settings**.
2.  Selecciona **Personal access tokens** > **Tokens (classic)**.
3.  Haz clic en **Generate new token (classic)**.
4.  En "Scopes", marca la casilla **`repo`** (control total de repos privados).
5.  **COPIA** ese código largo (empieza por `ghp_...`). *Guárdalo bien.*

---

## 🔐 3. Configuración de Credenciales

Configura Git para que recuerde tu token.

### 🪟 En Windows
Windows suele usar el "Credential Manager". Al clonar o subir cambios, si sale una ventana emergente, elige **"Token"** y pega tu código `ghp_...`.

### 🐧 En Ubuntu (Linux)
Ejecuta esto en la terminal para guardar tus datos y no escribirlos siempre:

```bash
git config --global user.name "TuUsuarioGitHub"
git config --global user.email "tu_email@ejemplo.com"
git config --global credential.helper store
```

---

## 🚀 4. Clonar el Repositorio (Primera vez)

```bash
git clone https://github.com/SVN11X/tesis_black_robot.git
```

* **Username:** Tu usuario.
* **Password:** Pega tu **Token** (En Linux no se verán asteriscos al pegar, es normal).

---

## 🔄 5. Flujo de Trabajo Diario

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