#!/bin/bash

# This script installs the picframe application and all its dependencies.
# It should be run with sudo.

set -e # Exit immediately if a command exits with a non-zero status.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

PICFRAME_DIR=$(dirname "$(realpath "$0")")/..
PICFRAME_USER=${SUDO_USER:-$(whoami)}

echo "Starting picframe installation..."
echo "Project directory: $PICFRAME_DIR"
echo "Running as user: $PICFRAME_USER"

# --- 1. System Dependencies ---
echo "Updating package list and installing system dependencies..."
apt-get update
apt-get install -y \
    git \
    python3-pip \
    python3-venv \
    libopenjp2-7 \
    libtiff5 \
    libatlas-base-dev \
    ffmpeg \
    mpv \
    samba-client \
    cec-utils \
    build-essential

# --- 2. System Configuration ---
echo "Applying system configurations..."

# Add user to the video group for framebuffer and CEC access
echo "Adding user '$PICFRAME_USER' to the 'video' group..."
usermod -a -G video "$PICFRAME_USER"

# Disable console cursor blinking
echo "Disabling console cursor blink..."
if ! grep -q "consoleblank=0" /boot/firmware/cmdline.txt; then
    sed -i '1 s/$/ consoleblank=0/' /boot/firmware/cmdline.txt
fi

# --- 3. Python Virtual Environment and Application ---
echo "Setting up Python virtual environment and installing picframe..."
cd "$PICFRAME_DIR"
# Run as the actual user to avoid creating root-owned files in the user's home
sudo -u "$PICFRAME_USER" bash << EOF
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install wheel
pip install .
deactivate
EOF

# --- 4. Make Scripts Executable ---
echo "Making shell scripts executable..."
chmod +x "$PICFRAME_DIR"/scripts/*.sh

# --- 5. Systemd Service for picframe ---
echo "Creating and enabling systemd service for picframe..."
cat > /etc/systemd/system/picframe.service << EOF
[Unit]
Description=PicFrame Slideshow Service
After=network.target

[Service]
User=$PICFRAME_USER
Group=video
WorkingDirectory=$PICFRAME_DIR
ExecStart=$PICFRAME_DIR/scripts/watcher.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable picframe.service

# --- 6. Cron Jobs ---
echo "Setting up cron jobs..."
# Create a temporary crontab file
CRON_FILE="/tmp/picframe_cron"

# Write cron jobs, ensuring they run as the correct user
cat > "$CRON_FILE" << EOF
# Picframe cron jobs
*/5 * * * * $PICFRAME_DIR/scripts/sync_photos.sh >> $PICFRAME_DIR/logs/sync_photos.log 2>&1
*/15 * * * * $PICFRAME_DIR/venv/bin/python $PICFRAME_DIR/scripts/pir_manager.py >> $PICFRAME_DIR/logs/pir_manager.log 2>&1
EOF

crontab -u "$PICFRAME_USER" "$CRON_FILE"
rm "$CRON_FILE"

echo "----------------------------------------------------"
echo "Installation complete!"
echo "A reboot is recommended to apply all changes (user group, kernel parameters)."
echo "You can start the service manually with: sudo systemctl start picframe.service"
echo "----------------------------------------------------"