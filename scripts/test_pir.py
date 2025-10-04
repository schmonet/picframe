#!/usr/bin/env python3

# ========================================================================================
#
# PIR Sensor and State Test Script for Picframe
#
# This script is a diagnostic tool for testing the PIR sensor and the different
# power states managed by the `pir_manager.py` script. It allows you to manually
# cycle through the ON, HOLD, BLACK, and OFF states to verify that the display,
# service, and slideshow pause/resume commands are working as expected.
# It also provides a continuous read-out of the PIR sensor's state.
#
# Author of modifications: Martin Schmalohr
# AI-assisted development: Google's Gemini
#
# ========================================================================================

import time
import subprocess
import yaml
import urllib.request
import urllib.error

try:
    import RPi.GPIO as GPIO
except Exception:
    print("RPi.GPIO not found. Please install it (`pip install RPi.GPIO`) and run as root.")
    exit(1)

# --- Configuration ---
PIR_PIN = 4
PICFRAME_SERVICE = "picframe.service"
CONFIG_PATH = "~/picframe/configuration.yaml"

def run_command(cmd):
    """Executes a shell command."""
    print(f"Executing: {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print(f"Error running command: {cmd}\n{e}")

def set_pause(pause: bool, port: int):
    """Pauses or unpauses the slideshow via HTTP call."""
    state = "true" if pause else "false"
    url = f"http://localhost:{port}/?paused={state}"
    try:
        print(f"Sending HTTP request to {url}")
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status != 200:
                print(f"Error: Received status code {response.status} from {url}")
    except urllib.error.URLError as e:
        print(f"Error sending HTTP request to {url}: {e}")

def main():
    # --- Load Config ---
    http_port = 9000 # Default port
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            http_config = config.get('http', {})
            http_port = http_config.get('port', 9000)
    except Exception as e:
        print(f"Warning: Could not read config file at {CONFIG_PATH}: {e}. Using default http port {http_port}.")

    print("\n--- Starting State Sequence Test ---")

    # 1. STATE_ON
    print("\n--- Testing STATE_ON ---")
    print("Turning display ON and starting service.")
    run_command("echo 'on 0' | cec-client -s -d 1")
    run_command(f"sudo systemctl start {PICFRAME_SERVICE}")
    set_pause(False, http_port)
    time.sleep(10)

    # 2. STATE_HOLD
    print("\n--- Testing STATE_HOLD ---")
    print("Sending HTTP request to PAUSE slideshow.")
    set_pause(True, http_port)
    time.sleep(10)

    # 3. Resume from HOLD
    print("\n--- Resuming from STATE_HOLD ---")
    print("Sending HTTP request to RESUME slideshow.")
    set_pause(False, http_port)
    time.sleep(10)

    # 4. STATE_BLACK
    print("\n--- Testing STATE_BLACK ---")
    print("Turning display OFF (service remains running).")
    run_command("echo 'standby 0' | cec-client -s -d 1")
    time.sleep(10)

    # 5. Resume from BLACK
    print("\n--- Resuming from STATE_BLACK ---")
    print("Turning display ON.")
    run_command("echo 'on 0' | cec-client -s -d 1")
    time.sleep(10)

    # 6. STATE_OFF
    print("\n--- Testing STATE_OFF ---")
    print("Turning display OFF and stopping service.")
    run_command("echo 'standby 0' | cec-client -s -d 1")
    run_command(f"sudo systemctl stop {PICFRAME_SERVICE}")
    time.sleep(10)

    # --- Restore to a known good state (ON) ---
    print("\n--- Test sequence finished. Restoring to STATE_ON. ---")
    run_command("echo 'on 0' | cec-client -s -d 1")
    run_command(f"sudo systemctl start {PICFRAME_SERVICE}")
    print("Waiting for picframe service to start...")
    time.sleep(5) # Allow http server to start
    set_pause(False, http_port)
    
    print("\nPausing for 5 seconds before starting PIR reading...")
    time.sleep(5)

    # --- Continuous PIR sensor reading ---
    print("\n--- Starting continuous PIR sensor reading ---")
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIR_PIN, GPIO.IN)
    last_state = -1
    try:
        while True:
            current_state = GPIO.input(PIR_PIN)
            if current_state != last_state:
                state_str = "MOTION DETECTED" if current_state == GPIO.HIGH else "Standby"
                print(f"[{time.strftime('%H:%M:%S')}] {state_str}")
                last_state = current_state
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nTest stopped by user.")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()
