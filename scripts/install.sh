#!/bin/bash

# ========================================================================================
#
# Picframe Installation Script (Safe Version - No Git Pull)
#
# This script automates the setup of the Picframe application and its custom
# modifications on a Raspberry Pi. It handles system dependencies, Python environment,
# service creation, and configuration for the PIR sensor and photo synchronization.
# It should be run with sudo.
#
# Author of modifications: Martin Schmalohr
# AI-assisted development: Google's Gemini
#
# ========================================================================================

# --- install.sh (v19, "Modell G" - Final Syntax Fix)

set -e # Exit immediately if a command exits with a non-zero status.

if [ "$EUID" -ne 0 ]; then
  echo "Please run as root (sudo)"
  exit 1
fi

# --- CONFIGURATION ---
# Reliably define directories using $HOME, which points to the current user's home directory.
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PICFRAME_DIR=$(realpath "$SCRIPT_DIR/..")
DATA_DIR="$PICFRAME_DIR/data"
CACHE_DIR="$PICFRAME_DIR/cache"

# --- Configuration Verification for Headless Operation ---

# This function checks for recommended settings for running PicFrame
# on a headless Raspberry Pi (without a desktop environment).

check_headless_settings() {
    # --- Configuration Paths ---
    # IMPORTANT: Adjust this path if your configuration.yaml is located elsewhere.
    CONFIG_YAML="$PICFRAME_DIR/configuration.yaml" 
    CMDLINE_TXT="/boot/cmdline.txt"
    CONFIG_TXT="/boot/config.txt"

    # --- Expected Settings ---
    EXPECTED_CMDLINE="video=HDMI-A-1:1920x1080@50"
    EXPECTED_CONFIG_OVERLAY="dtoverlay=vc4-kms-v3d"

    # --- State & Messaging ---
    local all_ok=true
    local error_messages=""

    # --- Check 1: configuration.yaml ---
    if [ -f "$CONFIG_YAML" ]; then
        # Check for 'use_glx: false'
        if ! grep -q -E "^\s*use_glx:\s*false" "$CONFIG_YAML"; then
            all_ok=false
            error_messages+="[FAIL] In '$CONFIG_YAML', 'use_glx' is not set to 'false'.\n"
        fi
        # Check for 'use_sdl2: true'
        if ! grep -q -E "^\s*use_sdl2:\s*true" "$CONFIG_YAML"; then
            all_ok=false
            error_messages+="[FAIL] In '$CONFIG_YAML', 'use_sdl2' is not set to 'true'.\n"
        fi
    else
        all_ok=false
        error_messages+="[FAIL] Configuration file not found at '$CONFIG_YAML'.\n"
    fi

    # --- Check 2: /boot/cmdline.txt ---
    if [ -f "$CMDLINE_TXT" ]; then
        if ! grep -q "$EXPECTED_CMDLINE" "$CMDLINE_TXT"; then
            all_ok=false
            error_messages+="[FAIL] In '$CMDLINE_TXT', the required video mode is not set.\n       Expected to find: '$EXPECTED_CMDLINE'\n"
        fi
    else
        all_ok=false
        error_messages+="[FAIL] Boot file not found at '$CMDLINE_TXT'. This script seems not to be running on a Raspberry Pi.\n"
    fi

    # --- Check 3: /boot/config.txt ---
    if [ -f "$CONFIG_TXT" ]; then
        # Check for an uncommented 'dtoverlay=vc4-kms-v3d'
        if ! grep -q -E "^\s*$EXPECTED_CONFIG_OVERLAY" "$CONFIG_TXT"; then
            all_ok=false
            error_messages+="[FAIL] In '$CONFIG_TXT', the KMS video driver is not enabled.\n       Expected to find an uncommented line: '$EXPECTED_CONFIG_OVERLAY'\n"
        fi
    else
        all_ok=false
        error_messages+="[FAIL] Boot file not found at '$CONFIG_TXT'. This script seems not to be running on a Raspberry Pi.\n"
    fi

    # --- Final Verdict and User Prompt ---
    if [ "$all_ok" = true ]; then
        echo "[OK] All settings for headless operation are configured correctly."
    else
        echo "--------------------------------------------------------------------"
        echo "!!! WARNING: Recommended settings for headless operation are missing. !!!"
        echo ""
        echo "The following settings are required for Pi3D to work correctly on a"
        echo "headless system (i.e., without X11 or Wayland desktop environment)."
        echo "--------------------------------------------------------------------"
        echo -e "$error_messages"
        echo "It is recommended to fix these issues and restart the installation."
        
        read -p "Do you want to continue anyway? (y/N): " choice
        case "$choice" in 
          y|Y )
            echo "Continuing installation against recommendations..."
            ;;
          * )
            echo "Installation aborted by user."
            exit 1
            ;;
        esac
    fi
}

# --- Main script execution starts here ---

# Call the function to perform the checks
check_headless_settings

# ... rest of your install.sh script ...
echo "Proceeding with the rest of the installation..."

PICFRAME_USER=${SUDO_USER:-$(whoami)}

echo "Starting picframe installation..."
echo "Project directory: $PICFRAME_DIR"
echo "Running as user: $PICFRAME_USER"

# --- System Dependencies ---
echo "[1/12] Updating package list and installing system dependencies..."
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
    build-essential \
	cifs-utils \
	bc \
	libsdl2-dev  \
	python3-rpi.gpio  \
	edid-decode \
	libimage-exiftool-perl

# --- System Configuration ---
echo "Applying system configurations..."

# Set system locale
echo "[2/12] Setting system locale to de_DE.UTF-8..."
sudo raspi-config nonint do_change_locale de_DE.UTF-8

# Add user to the video group for framebuffer and CEC access
echo "[3/12] Adding user '$PICFRAME_USER' to grant hardware access (video, render, input groups)..."
usermod -a -G video,render,input "$PICFRAME_USER"

# Enable framebuffer blanking
echo "[4/12] Copying udev rule for framebuffer blanking..."
sudo cp "$PICFRAME_DIR/99-fb-blank.rules" /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger

# Disable console cursor blinking
echo "[5/12] Disabling console cursor blink..."
if ! grep -q "consoleblank=0" /boot/cmdline.txt; then
    sed -i '1 s/$/ consoleblank=0/' /boot/cmdline.txt
fi

# Enforce TTY Background Color
echo "[6/12] Forcibly set console background color after TTY init"
sudo "$PICFRAME_DIR/scripts/set_tty_color.sh"

# Login user to background session
# echo "Forcibly login to background session to prevent XDG_RUNTIME_DIR not set error"
# sudo loginctl enable-linger schmali

# Clone or update the repository
echo "[7/12] Clone picframe repository if not exists"
if [ -d "$PICFRAME_DIR" ]; then
    echo "Project directory exists. Skipping git pull to preserve local changes."
    # The 'git pull' command is intentionally disabled in this version.
else
    echo "Cloning picframe repository..."
    git clone "https://github.com/helgeerbe/picframe.git" "$PICFRAME_DIR"
fi

# --- Python Virtual Environment and Application ---
echo "[8/12] Setting up Python virtual environment and installing picframe..."
cd "$PICFRAME_DIR"

# If venv already exists, delete it, so that it will be recreated
if [ -d "$PICFRAME_DIR/venv" ]; then
    echo "Virtual environment 'venv' found. Cleaning up..."
	rm -rf "$PICFRAME_DIR/venv"
	echo "Virtual environment 'venv' cleaned up."
else
    echo "No virtual environment 'venv' found."
fi

# Run as the actual user to avoid creating root-owned files in the user's home
sudo -u "$PICFRAME_USER" bash << EOF
# Remove old virtual environment if it exists.
if [ -d "venv" ]; then
    rm venv -r
fi

# Create a new virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade core packaging tools
pip install --upgrade pip setuptools wheel

# Install the project in editable mode.
# This single command reads pyproject.toml and installs ALL dependencies.
pip install -e .

# Deactivate the virtual environment
deactivate
EOF

# --- Make Scripts Executable ---
echo "[9/12] Making shell scripts executable..."
chmod +x "$PICFRAME_DIR"/scripts/*.sh

# --- Systemd Service for picframe ---
echo "[10/12] Creating and enabling systemd service for picframe..."
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

# --- Systemd Service for pirmanager ---
echo "[11/12] Creating and enabling systemd service for pirmanager..."
cat > /etc/systemd/system/pir_manager.service << EOF
[Unit]
Description=PIR Sensor and Power Manager for PicFrame
After=network.target

[Service]
WorkingDirectory=$PICFRAME_DIR/scripts
ExecStart=$PICFRAME_DIR/venv/bin/python3 -u $PICFRAME_DIR/scripts/pir_manager.py
Restart=always
User=schmali

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable picframe.service
sudo systemctl enable pir_manager.service

# --- Cron Jobs ---
echo "[12/12] Setting up cron jobs..."
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
echo "Please review your configuration.yaml in /home/user/picframe/ to ensure all settings are correct."
echo "A reboot is recommended to apply all changes (user group, kernel parameters)."
echo "You can start the service manually with: sudo systemctl start picframe.service"
echo "----------------------------------------------------"