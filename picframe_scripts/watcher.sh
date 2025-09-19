#!/bin/bash
# This script is now a simple wrapper to start the picframe application.
# Album management and refilling are handled by the picframe Python application itself.

# --- CONFIGURATION ---
USER_HOME="/home/schmali"
PROJECT_DIR="$USER_HOME/picframe"
VENV_DIR="$PROJECT_DIR/venv"

# Start the picframe application
source "$VENV_DIR/bin/activate"
exec "$VENV_DIR/bin/picframe"