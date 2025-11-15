#!/bin/bash

# This script acts as a watcher for the picframe application.
# It runs picframe in a loop, allowing it to be restarted after
# certain events (like video playback) without terminating the service.

# Navigate to the directory of the script to ensure correct relative paths
cd "$(dirname "$0")/.."

while true; do
  # Run the picframe application using its virtual environment
  venv/bin/picframe
  EXIT_CODE=$?

  # Exit the watcher script if picframe exited with any code other than 10
  if [ $EXIT_CODE -ne 10 ]; then
    exit $EXIT_CODE
  fi
done