#!/bin/bash

# ========================================================================================
#
# Picframe Installation Script
#
# This script performs a complete setup of the picframe application and its
# surrounding ecosystem on a Raspberry Pi OS (or similar Debian-based) system.
#
# It handles:
# - System package dependencies (for python, pi3d, ffmpeg, smb, etc.)
# - Creation of a Python virtual environment.
# - Installation of all required Python packages.
# - Setup of the picframe systemd service for automatic startup.
# - Configuration of cron jobs for media synchronization.
#
# ========================================================================================

set -e # Exit immediately if a command exits with a non-zero status.

echo "### Starting PicFrame Installation ###"

# --- Configuration ---
PICFRAME_DIR=$(cd "$(dirname "$0")/.." && pwd)
USER=$(whoami)

# --- System Dependencies ---
echo "[1/5] Updating package list and installing system dependencies..."
sudo apt-get update
sudo apt-get install -y \
    python3-venv \
    python3-pip \
    libopenjp2-7 \
    libatlas-base-dev \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libswscale-dev \
    ffmpeg \
    cifs-utils \
    imagemagick \
    mediainfo \
    libimage-exiftool-perl

# --- Python Virtual Environment ---
echo "[2/5] Setting up Python virtual environment..."
if [ ! -d "$PICFRAME_DIR/venv" ]; then
    python3 -m venv "$PICFRAME_DIR/venv"
fi

# --- Python Dependencies ---
echo "[3/5] Installing Python packages into virtual environment..."
"$PICFRAME_DIR/venv/bin/pip" install --upgrade pip
"$PICFRAME_DIR/venv/bin/pip" install -r "$PICFRAME_DIR/requirements.txt"

# --- Systemd Service Setup ---
echo "[4/5] Setting up picframe systemd service..."

SERVICE_FILE="/etc/systemd/system/picframe.service"

sudo bash -c "cat > $SERVICE_FILE" << EOL
[Unit]
Description=PicFrame Service (Watcher Architecture)
After=network.target

[Service]
User=$USER
WorkingDirectory=$PICFRAME_DIR
ExecStart=$PICFRAME_DIR/scripts/watcher.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOL

echo "Reloading systemd daemon and enabling picframe service..."
sudo systemctl daemon-reload
sudo systemctl enable picframe.service

# --- Cron Job Setup ---
echo "[5/5] Setting up cron jobs for media synchronization..."

# Create a temporary cron file
CRON_TMP_FILE=$(mktemp)

# Add the sync job (runs every hour)
echo "0 * * * * $PICFRAME_DIR/scripts/sync_photos.sh >> $PICFRAME_DIR/sync.log 2>&1" > "$CRON_TMP_FILE"

# Install the new crontab
crontab "$CRON_TMP_FILE"
rm "$CRON_TMP_FILE"

echo "Cron job for sync_photos.sh has been set up to run hourly."


echo ""
echo "### Installation Complete! ###"
echo ""
echo "What's next?"
echo "1. Make sure your 'configuration.yaml' and 'scripts/sync_config.yaml' are correctly set up."
echo "2. You can start the picture frame now with: sudo systemctl start picframe.service"
echo "3. To check the status, use: sudo systemctl status picframe.service"
echo ""