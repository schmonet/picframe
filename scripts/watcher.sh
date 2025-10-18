#!/bin/bash

# ========================================================================================
#
# Picframe Service Watcher Script
#
# This script acts as a simple wrapper to launch the main Picframe application.
# It is intended to be called by the `picframe.service` systemd unit.
# Its primary role is to activate the correct Python virtual environment before
# executing the `picframe` command.
#
# Author of modifications: Martin Schmalohr
# AI-assisted development: Google's Gemini
#
# ========================================================================================

# This script is now a simple wrapper to start the picframe application.
# Album management and refilling are handled by the picframe Python application itself.

# --- CONFIGURATION ---
PROJECT_DIR="$HOME/picframe"
VENV_DIR="$PROJECT_DIR/venv"

# Start the picframe application
source "$VENV_DIR/bin/activate"
exec "$VENV_DIR/bin/picframe" "$PROJECT_DIR/configuration.yaml"