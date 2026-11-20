# 🤖 Tesis Black Robot - Access and Workflow Guide

Spanish version: [README.md](README.md)

This document explains how to install Git, clone the repository, and the workflow to pull or push changes.

---

## 🛠️ 1. Install Git

If Git is not installed:
* **🪟 Windows:** Download and install it from [git-scm.com](https://git-scm.com/download/win).
* **🐧 Ubuntu:** Run `sudo apt update && sudo apt install git -y`.

---

## ⚙️ 2. Set Your Identity

Git stores your name and email in every commit. Run this once:

```bash
git config --global user.name "TuUsuarioGitHub"
git config --global user.email "tu_email@ejemplo.com"
```

---

## 🚀 3. Clone the Repository (First time)

The repository is public, so cloning it asks for no credentials. Install Git LFS first, because the large mapping session files live there. The scripts expect the repository in `~/tesis_black_robot`:

```bash
sudo apt install git-lfs
git lfs install
git clone https://github.com/SVN11X/ros2-indoor-exploration-robot.git ~/tesis_black_robot
```

---

## 🔄 4. Daily Workflow

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
