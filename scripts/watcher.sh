#!/bin/bash

# Navigate to the project's root directory
SCRIPT_DIR=$(dirname "$(realpath "$0")")
PICFRAME_DIR=$(realpath "$SCRIPT_DIR/..")
cd $PICFRAME_DIR

export PICFRAME_RESTART_CODE=0 # Initial exit code

while true; do
  # Run the picframe application and pass the config file as an argument.
  # Capture the exit code immediately after.
  venv/bin/picframe -c $PICFRAME_DIR/configuration.yaml
  RESTART_CODE=$?

  # Exit the watcher script if picframe exited with any code other than 10 (video restart)
  if [ "$RESTART_CODE" -ne 10 ]; then
    exit $RESTART_CODE
  fi

  # Export the restart code for the next loop iteration if needed by the python script
  export PICFRAME_RESTART_CODE=$RESTART_CODE
done
