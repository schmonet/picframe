#!/bin/bash

# ========================================================================================
#
# Picframe Installation Script (Safe Version - No Git Pull)
#
# This script automates the setup of the Picframe application and its custom
# modifications on a Raspberry Pi. It handles system dependencies, Python environment,
# service creation, and configuration for the PIR sensor and photo synchronization.
#
# Author of modifications: Martin Schmalohr
# AI-assisted development: Google's Gemini
#
# ========================================================================================

# --- install.sh (v19, "Modell G" - Final Syntax Fix)

set -e

# --- SCRIPT LOGIC ---

echo "Starting Picframe Final Setup (Safe Mode - No Git Pull)..."

# Safety check: Do not run as root
if [ "$EUID" -eq 0 ]; then
  echo "ERROR: Please run this script as your normal user (e.g., 'schmali'), not as root or with sudo."
  echo "The script will ask for your sudo password when it needs elevated permissions."
  exit 1
fi

# --- CONFIGURATION ---
# Reliably define directories using $HOME, which points to the current user's home directory.
PROJECT_DIR="$HOME/picframe"
SCRIPT_DIR="$PROJECT_DIR/scripts"
DATA_DIR="$PROJECT_DIR/data"
CACHE_DIR="$PROJECT_DIR/cache"
LIVE_DIR="$PROJECT_DIR/live"
VENV_DIR="$PROJECT_DIR/venv"


# 1. Install system dependencies
echo "[1/9] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y git python3-pip python3-venv cifs-utils bc vlc libsdl2-dev python3-rpi.gpio cec-utils edid-decode libimage-exiftool-perl ffmpeg

# 2. Set system locale
echo "[2/9] Setting system locale to de_DE.UTF-8..."
sudo raspi-config nonint do_change_locale de_DE.UTF-8

# 3. Clone or update the repository
if [ -d "$PROJECT_DIR" ]; then
    echo "[3/9] Project directory exists. Skipping git pull to preserve local changes."
    # The 'git pull' command is intentionally disabled in this version.
else
    echo "[3/9] Cloning picframe repository..."
    git clone "https://github.com/helgeerbe/picframe.git" "$PROJECT_DIR"
fi

# 4. Create Python Virtual Environment and install dependencies
echo "[4/9] Creating/updating Python virtual environment and dependencies..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install RPi.GPIO Pillow defusedxml pi3d PyYAML paho-mqtt IPTCInfo3 numpy ninepatch pi_heif python-vlc
deactivate

# 5. Install the picframe package with testing extras
echo "[5/9] Installing picframe in editable mode with testing extras..."
source "$VENV_DIR/bin/activate"
pip install -e "$PROJECT_DIR[test]"
deactivate

# 6. Create external directories and static config
echo "[6/9] Creating external directories and static config..."
mkdir -p "$DATA_DIR/data" "$DATA_DIR/config" "$CACHE_DIR"
CONFIG_FILE_PATH="$DATA_DIR/config/configuration.yaml"

echo "Static configuration file generation skipped. Please ensure $CONFIG_FILE_PATH is correctly configured."

# Always copy fresh data files
cp -r "$PROJECT_DIR/src/picframe/data/"* "$DATA_DIR/data/"


# 7. Grant hardware access permissions
echo "[7/9] Granting user '$USER' hardware access (video, render, input groups)..."
sudo usermod -a -G video,render,input $USER

echo "Copying udev rule for framebuffer blanking..."
sudo cp "$PROJECT_DIR/99-fb-blank.rules" /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger


# 8. Create and enable systemd services
echo "[8/9] Creating and enabling systemd services with hardcoded paths..."

# --- picframe.service ---
# Using hardcoded absolute paths to avoid any systemd interpretation issues.
cat << EOF | sudo tee /etc/systemd/system/picframe.service
[Unit]
Description=PicFrame Service (Watcher Architecture)
After=network.target

[Service]
WorkingDirectory=/home/schmali/picframe
ExecStart=/home/schmali/picframe/scripts/watcher.sh
Restart=on-failure
User=schmali
Environment="XDG_RUNTIME_DIR=/run/user/1000"

[Install]
WantedBy=multi-user.target
EOF

# --- pir_manager.service ---
cat << EOF | sudo tee /etc/systemd/system/pir_manager.service
[Unit]
Description=PIR Sensor and Power Manager for PicFrame
After=network.target

[Service]
ExecStart=/home/schmali/picframe/venv/bin/python3 -u /home/schmali/picframe/scripts/pir_manager.py
WorkingDirectory=/home/schmali/picframe/scripts
Restart=always
User=schmali

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable picframe.service
sudo systemctl enable pir_manager.service

# Correctly print multi-line message using a here-document
cat << "EOF"

Setup for Watcher Architecture complete!

--------------------------------------------------
!!! IMPORTANT NEXT STEPS !!!
--------------------------------------------------

1.  REVIEW PICFRAME CONFIG:
    Please review your configuration file to ensure all settings are correct.

2.  REBOOT THE SYSTEM to apply all changes, especially group permissions.

EOF