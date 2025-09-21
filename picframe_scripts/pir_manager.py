#!/usr/bin/env python3

# ========================================================================================
#
# PIR Sensor and Power Manager for Picframe
#
# This script manages the power of the display and the Picframe service based on
# motion detection from a PIR sensor and a predefined day/night schedule.
# It aims to reduce power consumption by turning off the display and stopping the
# service when no motion is detected for a certain period or during the night.
#
# Author of modifications: Martin Schmalohr
# AI-assisted development: Google's Gemini
#
# ========================================================================================

import time
import subprocess
import os
from datetime import datetime
import yaml
import urllib.request
import urllib.error

try:
    import RPi.GPIO as GPIO
except Exception as e:
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    print(f"!!! CRITICAL: Failed to import RPi.GPIO. Using mock library.!!!")
    print(f"!!! Motion detection will not work. Error: {e}              !!!")
    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    class MockGPIO:
        BCM = 0
        IN = 0
        HIGH = 1
        LOW = 0
        def setmode(self, m): pass
        def setup(self, p, m): pass
        def input(self, p): return 0
        def cleanup(self): pass
    GPIO = MockGPIO()

# --- Configuration ---
PIR_PIN = 4  # GPIO pin of the PIR sensor
HOLDSCRREN_TIMEOUT_S = 3600  # 1 hour of inactivity to pause the slideshow
BLACKSCREEN_TIMEOUT_S = 10800  # 3 hours of inactivity for a black screen
NIGHT_START_HOUR = 0  # 00:00
NIGHT_END_HOUR = 6    # 06:00
LOOP_SLEEP_S = 5.0    # Time between checks (5.0 seconds)
PICFRAME_SERVICE = "picframe.service"
CONFIG_PATH = "/home/schmali/picframe_data/config/configuration.yaml"

# --- States ---
STATE_ON = "ON"
STATE_HOLD = "HOLD"
STATE_BLACK = "BLACK"
STATE_OFF = "OFF"

def run_command(cmd):
    """Executes a shell command."""
    try:
        subprocess.run(cmd, shell=True, check=True)
    except Exception as e:
        print(f"Error running command: {cmd}\n{e}")

def set_service(is_active):
    """Starts or stops the picframe service."""
    action = "start" if is_active else "stop"
    print(f"Turning picframe service {action}...")
    run_command(f"sudo systemctl {action} {PICFRAME_SERVICE}")

def set_display_power(is_on):
    """Turns the display on or off using cec-client."""
    if is_on:
        print("Turning display on with cec-client...")
        run_command("echo 'on 0' | cec-client -s -d 1")
    else: # is_on is False
        print("Turning display off with cec-client...")
        run_command("echo 'standby 0' | cec-client -s -d 1")

def set_pause(pause: bool, port: int):
    """Pauses or unpauses the slideshow via HTTP call. Returns True on success."""
    state = "true" if pause else "false"
    url = f"http://localhost:{port}/?paused={state}"
    try:
        print(f"Sending HTTP request to {url}")
        with urllib.request.urlopen(url, timeout=10) as response:
            status_code = response.status
            print(f"Received response with status: {status_code}")
            if status_code == 200:
                return True
            else:
                print(f"Error: Received status code {status_code} from {url}")
                try:
                    body = response.read().decode('utf-8', errors='ignore')
                    print(f"Response body: {body}")
                except Exception as read_e:
                    print(f"Could not read response body: {read_e}")
                return False
    except urllib.error.URLError as e:
        print(f"Error sending HTTP request to {url}: {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred in set_pause: {e}")
        return False

def set_pause_with_retry(pause: bool, port: int):
    """Calls set_pause with a retry mechanism for startup robustness."""
    action_str = "pause" if pause else "unpause"
    print(f"Attempting to {action_str} slideshow (with retries)...")
    for attempt in range(10):  # Try for up to 30 seconds (10 * 3s)
        if set_pause(pause, port):
            print(f"Successfully {action_str}d slideshow.")
            return
        else:
            if attempt < 9:
                print(f"Attempt {attempt + 1}/10 failed. Retrying in 3 seconds...")
                time.sleep(3)
            else:
                print(f"Could not {action_str} slideshow after 10 attempts. Continuing anyway.")

def main():
    """Main function."""
    # --- Load Config ---
    http_port = 9000 # Default port
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = yaml.safe_load(f)
            http_config = config.get('http', {})
            http_port = http_config.get('port', 9000)
    except Exception as e:
        print(f"Warning: Could not read config file at {CONFIG_PATH}: {e}. Using default http port {http_port}.")

    # --- GPIO Setup ---
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIR_PIN, GPIO.IN)
    
    last_motion_time = time.monotonic()
    current_state = STATE_ON
    last_motion_state = False
    
    print("---PIR Manager Started---")
    set_display_power(True) # Ensure display is on at start
    set_service(True)
    set_pause_with_retry(False, http_port) # Ensure slideshow is not paused

    try:
        while True:
            now = datetime.now()
            if NIGHT_START_HOUR < NIGHT_END_HOUR:  # For night periods that don't cross midnight (e.g., 0:00-6:00)
                is_night = NIGHT_START_HOUR <= now.hour < NIGHT_END_HOUR
            else:  # For night periods that cross midnight (e.g., 22:00-6:00)
                is_night = now.hour >= NIGHT_START_HOUR or now.hour < NIGHT_END_HOUR
            motion_detected = GPIO.input(PIR_PIN) == GPIO.HIGH
            inactivity_time = time.monotonic() - last_motion_time

            if motion_detected:
                last_motion_time = time.monotonic()
                if current_state != STATE_ON:
                    print("Motion detected. Resuming normal operation.")
                    if current_state == STATE_OFF:
                        run_command("sudo rfkill unblock wifi")
                        set_display_power(True)
                        set_service(True)
                        set_pause_with_retry(False, http_port)
                    else:  # Covers STATE_BLACK and STATE_HOLD
                        if current_state == STATE_BLACK:
                            set_display_power(True)
                        set_pause_with_retry(False, http_port) # Always unpause if not OFF
                    current_state = STATE_ON
                else: # current_state is STATE_ON
                    if not last_motion_state: # and last state was no motion
                        print("Motion detected (normal operation). Resetting inactivity timer.")
            else:  # No motion
                if current_state == STATE_OFF and not is_night:
                    print("Day time. Resuming normal operation.")
                    run_command("sudo rfkill unblock wifi")
                    set_display_power(True)
                    set_service(True)
                    set_pause_with_retry(False, http_port)
                    last_motion_time = time.monotonic()
                    current_state = STATE_ON
                elif is_night:
                    if current_state != STATE_OFF:
                        print("Night time. Entering OFF mode.")
                        set_service(False)
                        set_display_power(False)
                        current_state = STATE_OFF
                elif inactivity_time > BLACKSCREEN_TIMEOUT_S:
                    if current_state != STATE_BLACK:
                        print(f"Inactivity for {int(inactivity_time/60)}min. Entering Blackscreen mode.")
                        set_display_power(False)
                        current_state = STATE_BLACK
                elif inactivity_time > HOLDSCRREN_TIMEOUT_S:
                    if current_state != STATE_HOLD and current_state != STATE_BLACK:
                        print(f"Inactivity for {int(inactivity_time/60)}min. Entering Holdscreen mode.")
                        set_pause_with_retry(True, http_port)
                        current_state = STATE_HOLD
            
            last_motion_state = motion_detected
            time.sleep(LOOP_SLEEP_S)

    except KeyboardInterrupt:
        print("PIR Manager stopped by user.")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()