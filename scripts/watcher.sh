#!/bin/bash

# Navigate to the directory of the script to ensure correct relative paths
cd "$(dirname "$0")/.."

export PICFRAME_RESTART_CODE=0 # Initial exit code
while true; do
  # Run the picframe application.
  # The python script will read the PICFRAME_RESTART_CODE environment variable.
  venv/bin/picframe
  RESTART_CODE=$?

  # Exit the watcher script if picframe exited with any code other than 10 (video restart)
  if [ $RESTART_CODE -ne 10 ]; then
    exit $RESTART_CODE
  fi
  export PICFRAME_RESTART_CODE=$RESTART_CODE
done