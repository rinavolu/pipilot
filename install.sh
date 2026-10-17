#!/bin/bash
# ==============================================================================
# PiPilot Automated Systemd Installer for Raspberry Pi OS / Debian
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="${SUDO_USER:-$(whoami)}"
SERVICE_NAME="pipilot.service"
SYSTEMD_PATH="/etc/systemd/system/${SERVICE_NAME}"
VENV_DIR="${SCRIPT_DIR}/venv"

echo "=========================================="
echo "Installing PiPilot as a system service"
echo "=========================================="
echo "Directory: $SCRIPT_DIR"
echo "Running as user: $CURRENT_USER"

# 1. Ensure Python 3 and venv package are installed
echo "Checking Python and virtual environment dependencies..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: python3 could not be found. Please install Python 3 first."
    exit 1
fi

# Debian/Raspberry Pi OS requires python3-venv for PEP 668 compliant virtual environments
if ! dpkg -s python3-venv &> /dev/null; then
    echo "python3-venv is required. Installing via apt..."
    sudo apt update && sudo apt install -y python3-venv python3-pip
fi

# 2. Setup Virtual Environment (fixes PEP 668 'externally-managed-environment' error)
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

echo "Installing Python dependencies inside virtual environment..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt"

# Ensure correct permissions if run with sudo
if [ -n "$SUDO_USER" ] && [ "$SUDO_USER" != "root" ]; then
    chown -R "$CURRENT_USER":"$CURRENT_USER" "$VENV_DIR"
fi

# 3. Configure passwordless sudo for power and service commands
echo "Configuring passwordless sudo permissions for $CURRENT_USER..."
SUDOERS_FILE="/etc/sudoers.d/010_${CURRENT_USER}-nopasswd"
if [ ! -f "$SUDOERS_FILE" ] || ! grep -q "NOPASSWD: ALL" "$SUDOERS_FILE" 2>/dev/null; then
    echo "${CURRENT_USER} ALL=(ALL) NOPASSWD: ALL" | sudo tee "$SUDOERS_FILE" > /dev/null
    sudo chmod 0440 "$SUDOERS_FILE"
fi

# 4. Check config.yaml
if [ ! -f "$SCRIPT_DIR/config.yaml" ]; then
    echo "WARNING: config.yaml not found! Copying from config.example.yaml..."
    cp "$SCRIPT_DIR/config.example.yaml" "$SCRIPT_DIR/config.yaml"
    echo "Please edit $SCRIPT_DIR/config.yaml with your Telegram bot token and admin chat ID."
fi

# 5. Generate customized systemd service unit
echo "Creating systemd service unit file..."

# Decommission legacy rpibridgebot service if present
if systemctl is-active --quiet rpibridgebot 2>/dev/null || [ -f "/etc/systemd/system/rpibridgebot.service" ]; then
    echo "Migrating from legacy rpibridgebot service to pipilot..."
    sudo systemctl stop rpibridgebot 2>/dev/null || true
    sudo systemctl disable rpibridgebot 2>/dev/null || true
    sudo rm -f "/etc/systemd/system/rpibridgebot.service"
fi

TEMP_SERVICE="/tmp/${SERVICE_NAME}"
cat <<EOF > "$TEMP_SERVICE"
[Unit]
Description=PiPilot - Raspberry Pi Telegram Remote Control & Monitoring
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${VENV_DIR}/bin/python3 ${SCRIPT_DIR}/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# 6. Copy to /etc/systemd/system/ (requires sudo)
echo "Registering service with systemd..."
sudo cp "$TEMP_SERVICE" "$SYSTEMD_PATH"
rm "$TEMP_SERVICE"

# 7. Reload systemd daemon and enable service
echo "Enabling and starting $SERVICE_NAME..."
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo ""
echo "=========================================="
echo "Installation complete!"
echo "PiPilot will now automatically start on boot (before login)."
echo ""
echo "Helpful commands:"
echo "  - View status:  sudo systemctl status $SERVICE_NAME"
echo "  - View logs:    sudo journalctl -u $SERVICE_NAME -f"
echo "  - Restart bot:  sudo systemctl restart $SERVICE_NAME"
echo "  - Stop bot:     sudo systemctl stop $SERVICE_NAME"
echo "=========================================="
