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
# Author of modifications: schmonet
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
        OUT = 1
        HIGH = 1
        LOW = 0
        def setmode(self, m): pass
        def setup(self, p, m): pass
        def input(self, p): return 0
        def output(self, p, v): pass
        def cleanup(self): pass
    GPIO = MockGPIO()

# --- Configuration ---
PIR_PIN = 18  # GPIO pin of the PIR sensor (BCM numbering, physical pin 12)
HOLDSCRREN_TIMEOUT_S = 3600   # 60 min of inactivity to pause the slideshow
BLACKSCREEN_TIMEOUT_S = 7200  # 2 hours of inactivity for a black screen
NIGHT_START_HOUR = 23 # 23:00
NIGHT_END_HOUR = 6    # 06:00
LOOP_SLEEP_S = 15.0    # Time between checks (15.0 seconds)
PICFRAME_SERVICE = "picframe.service"
CONFIG_PATH = "~/picframe/configuration.yaml"

# --- Display Power Control ---
# "cec"  : send HDMI-CEC standby/on commands via cec-client (works with CEC-compliant TVs, e.g. Sony).
# "gpio" : hard-switch the display's 5V supply via a MOSFET module (e.g. XY-MOS), needed for
#          displays that don't fully turn off their backlight on CEC standby (e.g. Verbatim #49593).
DISPLAY_POWER_METHOD = "gpio"
DISPLAY_POWER_PIN = 17  # BCM17 / physical pin 11 (generic GPIO, no special/hybrid function)
# True: GPIO HIGH switches the MOSFET/display ON, LOW = OFF. Flip to False if your module inverts.
DISPLAY_POWER_ACTIVE_HIGH = True

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
    """Turns the display on or off, either via HDMI-CEC or a hard GPIO power switch."""
    if DISPLAY_POWER_METHOD == "gpio":
        level = GPIO.HIGH if (is_on == DISPLAY_POWER_ACTIVE_HIGH) else GPIO.LOW
        print(f"Turning display {'on' if is_on else 'off'} via GPIO{DISPLAY_POWER_PIN} (5V switch)...")
        GPIO.output(DISPLAY_POWER_PIN, level)
    elif is_on:
        print("Turning display on with cec-client...")
        run_command("echo 'on 0' | cec-client -s -d 1")
    else: # is_on is False
        print("Turning display off with cec-client...")
        run_command("echo 'standby 0' | cec-client -s -d 1")

def disable_wifi_power_save():
    """Turns off WiFi power saving. On the Pi Zero 2 W (BCM43436), power saving can leave the
    WiFi chip hung after days of uptime ("brcmf_sdio_htclk: HT Avail request error: -110" flooding
    the kernel log), recoverable only by a cold boot. The driver re-enables power saving whenever
    the chip is re-initialized, so this is repeated after every rfkill unblock. The interface may
    need a few seconds to reappear after unblocking, hence the retries."""
    for attempt in range(5):
        result = subprocess.run("sudo iw wlan0 set power_save off", shell=True,
                                capture_output=True, text=True)
        if result.returncode == 0:
            print("WiFi power save disabled.")
            return
        time.sleep(2)
    print(f"Could not disable WiFi power save: {result.stderr.strip()}")

def set_wifi(is_on):
    """Blocks or unblocks the WiFi radio via rfkill and sets the no-WLAN flag for picframe."""
    if is_on:
        print("Turning WiFi on...")
        run_command("sudo rfkill unblock wifi")
        run_command("rm -f /dev/shm/picframe_nowlan.flag")
        disable_wifi_power_save()
    else:
        print("Turning WiFi off...")
        run_command("sudo rfkill block wifi")
        run_command("touch /dev/shm/picframe_nowlan.flag")

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
        with open(os.path.expanduser(CONFIG_PATH), 'r') as f:
            config = yaml.safe_load(f)
            http_config = config.get('http', {})
            http_port = http_config.get('port', 9000)
    except Exception as e:
        print(f"Warning: Could not read config file at {CONFIG_PATH}: {e}. Using default http port {http_port}.")

    # --- GPIO Setup ---
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(PIR_PIN, GPIO.IN)
    if DISPLAY_POWER_METHOD == "gpio":
        GPIO.setup(DISPLAY_POWER_PIN, GPIO.OUT)

    print("---PIR Manager Started---")

    # --- Night-aware startup ---
    # If the script (re)starts during the night window, go straight to OFF
    # instead of briefly turning everything on and blocking wifi a moment later.
    now = datetime.now()
    if NIGHT_START_HOUR < NIGHT_END_HOUR:
        is_night = NIGHT_START_HOUR <= now.hour < NIGHT_END_HOUR
    else:
        is_night = now.hour >= NIGHT_START_HOUR or now.hour < NIGHT_END_HOUR

    if is_night:
        print("Starting during night hours. Entering OFF mode immediately.")
        set_wifi(False)
        set_display_power(False)
        set_service(False)
        current_state = STATE_OFF
    else:
        set_wifi(True)
        set_display_power(True)
        set_service(True)
        set_pause_with_retry(False, http_port)
        current_state = STATE_ON

    last_motion_time = time.monotonic()
    last_motion_state = False

    try:
        while True:
            now = datetime.now()
            if NIGHT_START_HOUR < NIGHT_END_HOUR:  # For night periods that don't cross midnight (e.g., 0:00-6:00)
                is_night = NIGHT_START_HOUR <= now.hour < NIGHT_END_HOUR
            else:  # For night periods that cross midnight (e.g., 22:00-6:00)
                is_night = now.hour >= NIGHT_START_HOUR or now.hour < NIGHT_END_HOUR

            if is_night:
                # Night mode is absolute: no override, no PIR reaction. WiFi and
                # display stay off no matter what the PIR sensor reports.
                if current_state != STATE_OFF:
                    print("Night time. Entering OFF mode.")
                    set_wifi(False)
                    set_service(False)
                    set_display_power(False)
                    current_state = STATE_OFF
            else:
                if current_state == STATE_OFF:
                    print("Day time. Resuming normal operation.")
                    set_wifi(True)
                    set_display_power(True)
                    set_service(True)
                    set_pause_with_retry(False, http_port)
                    last_motion_time = time.monotonic()
                    current_state = STATE_ON

                motion_detected = GPIO.input(PIR_PIN) == GPIO.HIGH
                inactivity_time = time.monotonic() - last_motion_time

                if motion_detected:
                    last_motion_time = time.monotonic()
                    if current_state != STATE_ON:
                        print("Motion detected. Resuming normal operation.")
                        if current_state == STATE_BLACK:
                            set_display_power(True)
                        set_pause_with_retry(False, http_port) # Always unpause if not OFF
                        current_state = STATE_ON
                    else: # current_state is STATE_ON
                        if not last_motion_state: # and last state was no motion
                            print("Motion detected (normal operation). Resetting inactivity timer.")
                else:  # No motion
                    if inactivity_time > BLACKSCREEN_TIMEOUT_S:
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