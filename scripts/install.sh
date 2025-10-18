#!/bin/bash

# ========================================================================================
#
# Picframe Installation Script
#
# This script automates the setup of the Picframe application and its custom
# modifications on a Raspberry Pi. It handles system dependencies, Python environment,
# service creation, and configuration for the PIR sensor and photo synchronization.
#
# Author of modifications: Martin Schmalohr
# AI-assisted development: Google's Gemini
#
# ========================================================================================

# --- install.sh (v15, "Modell C" - Python-Managed Deletion) ---

set -e

# --- CONFIGURATION ---
USER_HOME="~/"
PROJECT_DIR="$USER_HOME/picframe"
SCRIPT_DIR="$PROJECT_DIR/scripts"
DATA_DIR="$USER_HOME/picframe/data"
CACHE_DIR="$USER_HOME/picframe/cache"
LIVE_DIR="$USER_HOME/picframe/live"
VENV_DIR="$PROJECT_DIR/venv"

# --- SCRIPT LOGIC ---

echo "Starting Picframe Final Setup for user 'schmali' (Python-Managed Deletion)..."

# 1. Install system dependencies
echo "[1/9] Installing system dependencies..."
sudo apt-get update
sudo apt-get install -y git python3-pip python3-venv cifs-utils bc vlc libsdl2-dev python3-rpi.gpio cec-utils edid-decode libimage-exiftool-perl ffmpeg

# 2. Set system locale
echo "[2/9] Setting system locale to de_DE.UTF-8..."
sudo raspi-config nonint do_change_locale de_DE.UTF-8

# 3. Clone or update the repository
if [ -d "$PROJECT_DIR" ]; then
    echo "[3/9] Project directory exists. Pulling latest changes..."
    cd "$PROJECT_DIR" && git pull && cd -
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

# 5. Install the picframe package
echo "[5/9] Installing picframe in editable mode..."
source "$VENV_DIR/bin/activate"
pip install -e "$PROJECT_DIR"
deactivate

# 6. Create external directories and static config
echo "[6/9] Creating external directories and static config..."
mkdir -p "$DATA_DIR/data" "$DATA_DIR/config" "$CACHE_DIR"
CONFIG_FILE_PATH="$DATA_DIR/config/configuration.yaml"

# Create static configuration for Picframe
# Removed as per user request to avoid overwriting existing configuration.yaml
# Users should manually configure configuration.yaml or copy from configuration_example.yaml

echo "Static configuration file generation skipped. Please ensure $CONFIG_FILE_PATH is correctly configured."

# Always copy fresh data files
cp -r "$PROJECT_DIR/src/picframe/data/"* "$DATA_DIR/data/"


# 7. Overwrite/Create all custom scripts and python modules
echo "[7/9] Creating/updating all custom scripts and python modules..."
echo "Skipping script generation as per user request. Please ensure scripts in picframe_scripts and src are up-to-date on the target system."


# 8. Create and enable systemd services
echo "[8/9] Creating and enabling systemd services..."

# --- picframe.service (for Watcher Architecture) ---
cat << EOF | sudo tee /etc/systemd/system/picframe.service
[Unit]
Description=PicFrame Service (Watcher Architecture)
After=network.target

[Service]
WorkingDirectory=$PROJECT_DIR
ExecStart=$SCRIPT_DIR/watcher.sh
Restart=on-failure
User=schmali
Environment="XDG_RUNTIME_DIR=/run/user/1000"

[Install]
WantedBy=multi-user.target
EOF

# --- pir_manager.service (remains the same) ---
cat << EOF | sudo tee /etc/systemd/system/pir_manager.service
[Unit]
Description=PIR Sensor and Power Manager for PicFrame
After=network.target

[Service]
ExecStart=$VENV_DIR/bin/python3 -u $SCRIPT_DIR/pir_manager.py
WorkingDirectory=$SCRIPT_DIR
Restart=always
User=schmali

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable picframe.service
sudo systemctl enable pir_manager.service

echo "
Setup for Watcher Architecture complete!

--------------------------------------------------
!!! IMPORTANT NEXT STEPS !!!
--------------------------------------------------

1.  REVIEW PICFRAME CONFIG:
    A static configuration has been generated at:
    $CONFIG_FILE_PATH
    Please review it to ensure all settings are correct.

2.  SET UP CRON JOB:
    - crontab -e
    - Add this line:

# Every hour from 6am to 11pm, sync new photos from server to cache
0 6-23 * * * /bin/bash $SCRIPT_DIR/sync_photos.sh >> /var/log/photo_sync.log 2>&1


3.  CREATE SMB CREDENTIALS if you haven't already.

4.  REBOOT THE SYSTEM to apply all changes.

EOF