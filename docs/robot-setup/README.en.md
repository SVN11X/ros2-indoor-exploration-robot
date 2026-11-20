# 🤖 Tesis Black Robot - Access and Workflow Guide

Spanish version: [README.md](README.md)

This document explains how to set up credentials, clone the private repository, and the workflow to pull or push changes.

> 🔒 **IMPORTANT:** Since this is a private repository, your usual GitHub password **WILL NOT work**. You must use a **Personal Access Token**.

---

## 🛠️ 1. Install Git

If Git is not installed:
* **🪟 Windows:** Download and install it from [git-scm.com](https://git-scm.com/download/win).
* **🐧 Ubuntu:** Run `sudo apt update && sudo apt install git -y`.

---

## 🔑 2. Generate your Access Token (Required)

You need a "special password" for the terminal:

1.  Go to your GitHub account > **Settings** > **Developer settings**.
2.  Select **Personal access tokens** > **Tokens (classic)**.
3.  Click **Generate new token (classic)**.
4.  Under "Scopes", check the **`repo`** box (full control of private repositories).
5.  **COPY** that long code (it starts with `ghp_...`). *Keep it safe.*

---

## 🔐 3. Credential Setup

Set up Git so it remembers your token.

### 🪟 On Windows
Windows usually uses the "Credential Manager". When you clone or push, if a pop-up window appears, choose **"Token"** and paste your `ghp_...` code.

### 🐧 On Ubuntu (Linux)
Run this in the terminal to save your details so you do not have to type them every time:

```bash
git config --global user.name "TuUsuarioGitHub"
git config --global user.email "tu_email@ejemplo.com"
git config --global credential.helper store
```

---

## 🚀 4. Clone the Repository (First time)

```bash
git clone https://github.com/SVN11X/tesis_black_robot.git
```

* **Username:** Your username.
* **Password:** Paste your **Token** (on Linux no asterisks appear when you paste, that is normal).

---

## 🔄 5. Daily Workflow

These are the commands you will use every time you work on the project. They work the same on Windows and Ubuntu.

### ⬇️ Step A: Get new changes (Git Pull)
**Before you start working**, always download the latest version to avoid conflicts.

```bash
git pull
```
*This downloads the progress your teammates pushed.*

### ⬆️ Step B: Push your changes (Git Push)
When you finish coding and want to save your work in the cloud:

1.  **Check what you changed (Optional):**
    ```bash
    git status
    ```
    *(Changed files appear in red).*

2.  **Stage the files:**
    ```bash
    git add .
    ```
    *(The dot `.` adds EVERYTHING you changed).*

3.  **Save the version (Commit):**
    ```bash
    git commit -m "Descripción breve de lo que hice"
    ```
    *(Example: `git commit -m "Arreglé el bug del sensor"`).*

4.  **Send to GitHub (Push):**
    ```bash
    git push
    ```

---
**Maintainer:** [SVN11X]
