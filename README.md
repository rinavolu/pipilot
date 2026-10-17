# PiPilot

> **A lightweight Telegram bot to remotely monitor, manage, and control your headless Raspberry Pi.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%20OS%20%7C%20Linux-red.svg?logo=raspberrypi&logoColor=white)](https://www.raspberrypi.com/)
[![Systemd](https://img.shields.io/badge/Service-Systemd-brightgreen.svg?logo=linux&logoColor=white)](https://systemd.io/)
[![Telegram](https://img.shields.io/badge/Interface-Telegram%20Bot%20API-blue.svg?logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Table of Contents

- [Overview](#overview)
- [Screenshots & Visual Tour](#screenshots--visual-tour)
- [Features](#features)
- [Quick Start (1-Step Installer)](#quick-start-1-step-installer)
- [How to Use PiPilot](#how-to-use-pipilot)
- [Configuration Guide](#configuration-guide)
- [Reflecting Config Changes on Your Pi](#reflecting-config-changes-on-your-pi)
- [Project Architecture](#project-architecture)
- [Useful Service Commands](#useful-service-commands)
- [Security & Access Guard](#security--access-guard)
- [License](#license)

---

## Overview

Operating a headless Raspberry Pi (home server, media streamer, smart home gateway, or background worker) usually requires opening an SSH terminal whenever you need to check CPU temperature, restart a stopped script, or inspect error logs.

**PiPilot** bridges that gap. It provides a secure, interactive Telegram interface directly from your smartphone or desktop:
- Receive an instant Telegram alert the moment your Pi boots up (before user login) with its current IP address and Wi-Fi network.
- Automatically receive periodic health reports (e.g. every 2 or 3 hours).
- Start, stop, and restart background services with confirmation dialogs.
- Tail and download full application `.log` files to your phone.
- Inspect active Java, Python, and JavaScript/Node.js processes.
- Safe power controls (reboot or shut down) with double confirmation.

---

## Screenshots & Visual Tour

*(Screenshots can be added to your repository's `/docs/images/` or `assets/` directory and referenced below)*

| Interactive Dashboard | Real-Time Health & Telemetry | Service Control |
| :---: | :---: | :---: |
| <img width="454" height="235" alt="image" src="https://github.com/user-attachments/assets/5ef46735-5bdd-427b-9f08-559b95d47405" /> | <img width="398" height="310" alt="image" src="https://github.com/user-attachments/assets/bb42796c-4ee2-4d60-956d-e1c1a2d680b1" /> | <img width="279" height="222" alt="image" src="https://github.com/user-attachments/assets/35f641f4-09af-44d0-bda8-864333623ef4" /> |

| Log Tail & Download | Boot & Periodic Alerts | Process Inspectors |
| :---: | :---: | :---: |
| <img width="438" height="141" alt="image" src="https://github.com/user-attachments/assets/9cf2c2f7-3589-4b8a-80b5-c3f349e8010d" /> | <img width="393" height="253" alt="image" src="https://github.com/user-attachments/assets/47755548-7857-4c09-b9a2-7fdc17cc60fb" /> | <img width="413" height="252" alt="image" src="https://github.com/user-attachments/assets/ebe5f4f2-d944-43f9-9548-ab65386ea723" /> |

---

## Features

- **Instant Boot Notification**: Sends a notification card immediately when your Pi powers on and connects to the network (before login) with local IPv4, Wi-Fi SSID, CPU temperature, and uptime.
- **Configurable Periodic Status Reports**: Automatically broadcast system metrics at custom minute intervals (e.g. every 120 or 180 minutes).
- **Native System Health Monitoring**: Real-time telemetry powered by `psutil` (CPU load, CPU temperature, RAM usage, and SD card disk space) with no external shell script dependencies.
- **Network & Connectivity Discovery**: Identify which Wi-Fi network the Pi is connected to and its assigned IP addresses (`wlan0`, `eth0`).
- **Dynamic Service Lifecycle Management**: Control your custom applications (scripts or systemd services) with interactive start, stop, and restart buttons.
- **Log Inspection & Document Transfer**:
  - **Tail**: Preview the last 50 lines of an application log directly in your Telegram chat.
  - **Send Document**: Download full `.log` files straight to your device.
  - **Auto-Cleanup**: Option to automatically truncate (reset to 0 bytes) logs after sending to conserve limited SD card storage.
- **Multi-Runtime Process Inspectors**:
  - **Java**: Active JVM processes via `jps`.
  - **Python**: Running Python scripts, PIDs, and RAM consumption (excluding the bot itself).
  - **JavaScript**: Running Node.js, Bun, Deno scripts and live PM2 status tables.
- **Interactive Inline Keyboards**: Tap-to-click buttons eliminate the need to memorize long slash commands.
- **Security & Authorization Guard**: Blocks unauthorized users from controlling your hardware.
- **Configuration-Driven**: All applications and settings are stored in `config.yaml`—no need to edit Python source code to configure your Pi.

---

## Quick Start (1-Step Installer)

PiPilot includes an automated installer that sets up a dedicated virtual environment (PEP 668 compliant for Raspberry Pi OS Bookworm and Debian), configures passwordless sudo for reboot/shutdown commands, and registers a self-healing `systemd` daemon.

### 1. Clone & Enter Directory
```bash
git clone https://github.com/rinavolu/pipilot.git
cd pipilot
```

### 2. Configure Your Telegram Token & Chat ID
```bash
cp config.example.yaml config.yaml
nano config.yaml
```
- Paste your Telegram bot token from [@BotFather](https://t.me/BotFather).
- Enter your numeric Telegram Chat ID (message [@userinfobot](https://t.me/userinfobot) to find yours).
- Save with `Ctrl + O`, `Enter`, and exit with `Ctrl + X`.

### 3. Run the Automated Installer
```bash
chmod +x install.sh
./install.sh
```

**What the installer does automatically:**
1. Installs `python3-venv` and `python3-pip` via apt if missing.
2. Creates an isolated Python virtual environment (`venv`).
3. Installs dependencies (`pyTelegramBotAPI`, `PyYAML`, `psutil`).
4. Configures passwordless sudo for power commands in `/etc/sudoers.d/`.
5. Creates, enables, and starts the `pipilot.service` systemd daemon.

---

## How to Use PiPilot

Once installed, open Telegram and message your bot.

### 1. Interactive Menu (`/menu` or `/start`)
Send `/menu` to pull up the main dashboard:
- **System Health**: Displays CPU load, temperature, RAM, disk space, and uptime.
- **Network & IP**: Displays hostname, Wi-Fi SSID, and active network interfaces.
- **Services**: Lists all configured services to view status, start, stop, or restart.
- **View Logs**: Select any service to tail the last 50 lines or download the full log file.
- **Java / Python / JS Apps**: Inspect active processes and memory consumption.
- **Reboot / Shutdown**: Hardware power controls with confirmation prompts.

### 2. Direct Command Reference
| Command | Alias | Description |
| :--- | :--- | :--- |
| `/menu` | `/start` | Open the interactive control dashboard with buttons |
| `/status` | `/health`, `/pi_resources` | Hardware telemetry (CPU temp, usage, RAM, disk, uptime) |
| `/network` | `/ip`, `/connected_wifi` | Show Wi-Fi SSID and assigned IPv4 addresses |
| `/services` | — | Open list of configured services to start/stop/restart |
| `/logs` | `/send_all_logs` | Open log inspector menu |
| `/apps` | `/active_apps` | Overview of all active apps across Java, Python, and JS |
| `/py` | `/python` | List running Python scripts and RAM consumption |
| `/js` | `/node` | List running Node.js / PM2 applications |
| `/jps` | `/java` | List active JVM / Java processes |
| `/reboot` | `/pi_reboot` | Reboot the Raspberry Pi (prompts confirmation) |
| `/shutdown` | `/pi_shutdown` | Power off the Raspberry Pi (prompts confirmation) |
| `/help` | `/all_commands` | Display command reference list |

---

## Configuration Guide

All configuration options are explained in detail in the dedicated guide:
**[Read the Full CONFIGURATION.md Guide](CONFIGURATION.md)**

Quick preview of [config.example.yaml](config.example.yaml):
```yaml
bot:
  token: "YOUR_TELEGRAM_BOT_TOKEN_HERE"
  admin_chat_ids:
    - 123456789  # Your Telegram User ID
  send_startup_message: true

# Periodic health reports every 120 minutes (2 hours)
periodic_status:
  enabled: true
  interval_minutes: 120

# Applications to monitor and control
services:
  - id: "webapp"
    name: "Web Application"
    type: "custom" # "custom" or "systemd"
    start_cmd: "/home/pi/scripts/start_webapp.sh"
    stop_cmd: "/home/pi/scripts/stop_webapp.sh"
    log_file: "/home/pi/logs/webapp.log"

  - id: "worker"
    name: "Background Worker"
    type: "custom"
    start_cmd: "/home/pi/scripts/start_worker.sh"
    stop_cmd: "/home/pi/scripts/stop_worker.sh"
    log_file: "/home/pi/logs/worker.log"

# Process Inspectors
inspectors:
  java:
    enabled: true
    jps_path: "jps"
  python:
    enabled: true
    exclude_self: true
  javascript:
    enabled: true
    pm2_enabled: true
```

---

## Reflecting Config Changes on Your Pi

Because PiPilot runs continuously as a background `systemd` daemon, any changes made to `config.yaml` or Python files must be reloaded by restarting the service.

### Workflow:

```bash
# 1. Navigate to the PiPilot directory
cd ~/pipilot

# 2. Pull changes from Git (or edit directly with: nano config.yaml)
git pull

# 3. Restart the background service
sudo systemctl restart pipilot

# 4. Confirm it restarted cleanly
sudo systemctl status pipilot
```

To watch live activity logs in real-time:
```bash
sudo journalctl -u pipilot -f
```

---

## Project Architecture

```
pipilot/
├── bot.py                 # Telegram runtime, routers, and callback handlers
├── config_loader.py       # YAML parser, environment overrides, and config singleton
├── system_metrics.py      # Native psutil hardware metrics, Wi-Fi reader, and uptime
├── service_manager.py     # Service lifecycle, process inspectors (Py/JS/Java), and logs
├── keyboards.py           # Inline keyboard layouts and dynamic menus
├── config.yaml            # Active user configuration (git-ignored for security)
├── config.example.yaml    # Documented configuration template
├── pipilot.service        # Systemd service unit template
├── install.sh             # 1-step boot installation and systemd registrar
├── requirements.txt       # Dependencies (pyTelegramBotAPI, PyYAML, psutil)
├── .gitignore             # Git ignore file protecting config.yaml and venv
├── CONFIGURATION.md       # Comprehensive parameter reference guide
├── LICENSE                # MIT License
└── README.md              # Project documentation
```

---

## Useful Service Commands

| Action | Command |
| :--- | :--- |
| **Check bot status** | `sudo systemctl status pipilot` |
| **Follow live logs** | `sudo journalctl -u pipilot -f` |
| **Restart bot service** | `sudo systemctl restart pipilot` |
| **Stop bot service** | `sudo systemctl stop pipilot` |
| **Disable auto-start on boot** | `sudo systemctl disable pipilot` |
| **Re-enable auto-start on boot** | `sudo systemctl enable pipilot` |

---

## Security & Access Guard

- **Whitelisted Admin IDs**: PiPilot rejects any message or button callback originating from a user not listed in `admin_chat_ids`. Unauthorized access attempts are logged with their Telegram username and numeric ID.
- **Confirmation Prompts**: Sensitive actions (`reboot` and `shutdown`) require an explicit confirmation button tap before the system executes the command.
- **Safe Log Clearing**: The `truncate` post-send action resets file size without destroying Unix file descriptors, preventing application logging crashes.

---

## License

This project is licensed under the **MIT License** — feel free to modify, distribute, and use it for your personal and commercial Raspberry Pi setups.
