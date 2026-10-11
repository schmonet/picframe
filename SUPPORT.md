# SUPPORT

Troubleshooting cheat sheet for a running picframe installation on the Raspberry Pi Zero 2 WH.
All commands are meant to be run over SSH as the picframe user (paths below assume the default
install location `~/picframe`; adjust if your deployment differs).

## Overview: services, jobs, logs and flags

| Component | Type | What it does | Log |
|---|---|---|---|
| `picframe.service` | systemd | Runs `scripts/watcher.sh`, which (re)starts `picframe` as long as it exits with code `10` (video restart) | `~/picframe/picframe.log` (`log_file` in `configuration.yaml`, rotated daily, 7 days kept) + `journalctl -u picframe` |
| `pir_manager.service` | systemd | Polls the PIR sensor, drives the ON/HOLD/BLACK/OFF state machine, switches display power, WiFi (night) and `picframe.service` | `journalctl -u pir_manager` |
| `sync_photos.sh` | cron | Fills `~/picframe/cache` from the SMB share up to the configured quota (`scripts/sync_config.yaml`) | `~/picframe/sync.log` (path set in `crontab -l`) |
| `~/picframe/shown_albums.log` | file | Albums already shown (skipped by both picframe and sync) + last line = resume bookmark | – |

Status flags in `/dev/shm` (RAM, cleared on reboot), shown as icons by picframe:

| Flag | Set by | Meaning |
|---|---|---|
| `picframe_offline.flag` | `sync_photos.sh` | SMB server not pingable on last sync attempt |
| `picframe_download.flag` | `sync_photos.sh` | Sync currently running |
| `picframe_nowlan.flag` | `pir_manager.py` | WiFi blocked by night mode |
| `picframe_no_files.flag` | `model.py` | Playlist is empty |
| `picframe_scanning.flag` | `model.py` | Album list is being rebuilt |

```bash
ls -la /dev/shm/picframe_*.flag
```

## Services and cron

```bash
# Status (check the "Active: ... since" timestamp - see note below)
systemctl status picframe.service pir_manager.service

# Start / stop / restart
sudo systemctl restart picframe.service
sudo systemctl restart pir_manager.service

# Enabled at boot?
systemctl is-enabled picframe.service pir_manager.service

# Live logs / logs since today / since last boot
journalctl -u pir_manager -f
journalctl -u picframe --since today
journalctl -b -u pir_manager -u picframe

# picframe's own log file
tail -f ~/picframe/picframe.log

# Running processes (exactly ONE pir_manager.py expected; the grep line itself does not count)
pgrep -af pir_manager.py
pgrep -af "picframe -c"
pgrep -af sync_photos

# Cron jobs of the picframe user
crontab -l
```

> **After deploying changed files:** a running service keeps executing the code it loaded at
> start. Copying a new `pir_manager.py` or `src/picframe/*.py` to the Pi has no effect until the
> service is restarted. Compare the "Active since" timestamp with the time of the copy.

> **Do not start `pir_manager.py` from cron.** It is a persistent loop managed by
> `pir_manager.service` (`Restart=always`); a cron entry spawns duplicate processes fighting over
> the GPIOs. `crontab -l | grep pir_manager` must return nothing.

> **Night WiFi switching** is done by `pir_manager.py` (23:00-06:00). Extra
> `rfkill block/unblock wifi` cron entries are redundant.

## Problem: SD card full

```bash
# Overall disk usage
df -h /
df -h ~/picframe/cache

# Size of the media cache vs. photo quota (quota_gb in scripts/sync_config.yaml)
du -sh ~/picframe/cache
grep -A4 "^photo_sync:" ~/picframe/scripts/sync_config.yaml

# Orphaned .tmp album folders from aborted syncs.
# They are ignored by picframe (never shown, never deleted) but count against the quota.
find ~/picframe/cache -maxdepth 2 -name '*.tmp' -exec du -sh {} +

# Biggest directories in the home folder (logs, venv, cache, ...)
du -h --max-depth=2 ~ 2>/dev/null | sort -h | tail -20

# Size of log files
du -sh ~/picframe/picframe.log* ~/picframe/logs ~/picframe/scripts/*.log 2>/dev/null
journalctl --disk-usage
```

Cleanup (check the output above first):

```bash
# Remove orphaned .tmp album folders (only while no sync is running: pgrep -af sync_photos)
find ~/picframe/cache -maxdepth 2 -type d -name '*.tmp' -exec rm -rf {} +

# Shrink the systemd journal
sudo journalctl --vacuum-size=50M
```

## Problem: no pictures shown ("no pictures" image)

```bash
# Is the playlist empty?
ls -la /dev/shm/picframe_no_files.flag

# Which albums are currently in the local cache (visible to picframe)?
find ~/picframe/cache -mindepth 2 -maxdepth 2 -type d ! -name '*.tmp'

# Number of image files in the cache
find ~/picframe/cache -type f -iregex '.*\.\(jpg\|jpeg\|png\|heic\)' | wc -l

# Shown-albums log: size and last entries (last line may be the resume bookmark)
wc -l ~/picframe/shown_albums.log
tail -5 ~/picframe/shown_albums.log

# Albums in the cache that are NOT yet marked as shown
comm -23 <(find ~/picframe/cache -mindepth 2 -maxdepth 2 -type d ! -name '*.tmp' | sort) \
         <(sort ~/picframe/shown_albums.log)

# What picframe did recently
grep -E "Switching to album|Playlist populated|All albums shown|No albums found|Triggering initial sync" \
     ~/picframe/picframe.log | tail -20
```

Typical causes:

* **Cache empty and sync did not refill it:** see "SMB / server unreachable" and check the sync log
  for `quota is full` (often caused by orphaned `.tmp` folders, see "SD card full").
* **Host not in WiFi** (also during the day): see next section.
* **Albums on disk but not yet in the database:** the image cache indexes new folders in the
  background; on a Pi Zero this can take a while after a large sync. Wait, then check again.

## Problem: SMB / server unreachable, sync not working

```bash
# WiFi state (blocked by rfkill? connected? IP address?)
rfkill list wifi
nmcli device status
nmcli -f GENERAL.STATE,GENERAL.CONNECTION,IP4.ADDRESS device show wlan0
iwconfig wlan0 2>/dev/null | grep -E "ESSID|Signal|Power Management"
ls -la /dev/shm/picframe_nowlan.flag   # present = night mode blocked WiFi

# Server reachable? (server_ip from scripts/sync_config.yaml)
SERVER_IP=$(sed -n 's/^ *server_ip: *"\{0,1\}\([^"]*\)"\{0,1\}.*/\1/p' ~/picframe/scripts/sync_config.yaml)
ping -c 3 "$SERVER_IP"

# Last sync runs (use the log path from crontab -l)
crontab -l | grep sync_photos
grep -E "not reachable|CRITICAL|quota is full|Downloading|Finalizing|No year directories" \
     ~/picframe/sync.log | tail -30

# Is a sync currently running / is the share still mounted?
pgrep -af sync_photos
mount | grep cifs

# Run a sync manually and watch the output (only when no other sync is running)
~/picframe/scripts/sync_photos.sh

# Test the SMB mount by hand (share name and credentials file from sync_config.yaml)
sudo mkdir -p /mnt/test_share
sudo mount -t cifs "//$SERVER_IP/Fotos" /mnt/test_share \
     -o credentials=$HOME/.smb_credentials,vers=3.0,uid=$(id -u),gid=$(id -g)
ls /mnt/test_share | head
sudo umount /mnt/test_share
```

WiFi recovery:

```bash
sudo rfkill unblock wifi
sudo nmcli radio wifi off && sudo nmcli radio wifi on
sudo systemctl restart NetworkManager
# Last resort: power cycle the Pi (a soft reboot does not always reset the WiFi chip)
```

To check whether WiFi power saving is active (a frequent cause of WiFi drop-outs on Pi Zero),
see the `Power Management` line of `iwconfig wlan0` above.

## Display power: HDMI-CEC vs. 5V power switch

The method is selected by constants at the top of `scripts/pir_manager.py` and
`scripts/test_pir.py` (keep both in sync):

```python
DISPLAY_POWER_METHOD = "gpio"     # "cec" or "gpio"
DISPLAY_POWER_PIN = 17            # BCM17 / physical pin 11
DISPLAY_POWER_ACTIVE_HIGH = True  # GPIO HIGH = display on
```

```bash
# Which method is configured on the Pi?
grep -nE "^DISPLAY_POWER_(METHOD|PIN|ACTIVE_HIGH)" ~/picframe/scripts/pir_manager.py ~/picframe/scripts/test_pir.py

# What pir_manager did recently
journalctl -u pir_manager --since today | grep -E "Turning display|state|Night|Day time"
```

### Method "cec" (HDMI-CEC via cec-client)

For CEC-compliant TVs only (e.g. the Sony test TV). Portable displays like the Verbatim #49593
do not turn off their backlight on CEC standby.

```bash
# List CEC adapters and scan the bus
cec-client -l
echo 'scan' | cec-client -s -d 1

# Query power state of TV (logical address 0)
echo 'pow 0' | cec-client -s -d 1

# Switch off / on manually
echo 'standby 0' | cec-client -s -d 1
echo 'on 0' | cec-client -s -d 1
```

### Method "gpio" (hard 5V switch via power switch module)

The display's 5V supply is switched by a **Pololu Mini Pushbutton Power Switch with Reverse
Voltage Protection, LV** (<https://eckstein-shop.de/PololuMiniPushbuttonPowerSwitchwithReverseVoltageProtection2CLV>), driven by BCM17 via its control
input (the pushbutton is not used). It is a **high-side** switch (switches +5V, GND of input and
output is shared), see Pololu's product page for the control pin behavior. A low-side module that only switches GND (e.g.
XY-MOS D4184) does **not** work: current flows back through the HDMI cable shield and the
display stays at ~4.9 V.

```bash
# Current level of the trigger pin (does not change it)
pinctrl get 17

# Manual switching (stop pir_manager first, otherwise it overrides the pin within seconds)
sudo systemctl stop pir_manager.service
pinctrl set 17 op dh    # drive high -> display ON  (with ACTIVE_HIGH = True)
pinctrl set 17 op dl    # drive low  -> display OFF
sudo systemctl start pir_manager.service
```

Hardware check with a multimeter: measure the voltage at the module's OUT +/- (display side).
Expected: ~5 V when on, 0 V when off, **with the HDMI cable connected**. If it only drops to 0 V
with HDMI unplugged, the module switches the wrong side (see above).

## PIR sensor check

The PIR sensor (RCW-0506) is on BCM18 / physical pin 12.

```bash
# Read the sensor level once (1 = motion)
pinctrl get 18

# Watch the sensor live (Ctrl+C to stop)
watch -n 0.5 pinctrl get 18

# What pir_manager reacted to
journalctl -u pir_manager --since "1 hour ago"
```

Full interactive state test (cycles ON -> HOLD -> BLACK -> OFF, then reads the PIR continuously).
Stop `pir_manager` first so both scripts don't drive the GPIOs at the same time:

```bash
sudo systemctl stop pir_manager.service
cd ~/picframe && venv/bin/python3 scripts/test_pir.py
sudo systemctl start pir_manager.service
```

Notes:

* During night mode (23:00-06:00) PIR motion is **intentionally ignored**; the display, WiFi and
  `picframe.service` stay off.
* Timeouts (`HOLDSCRREN_TIMEOUT_S`, `BLACKSCREEN_TIMEOUT_S`, `NIGHT_START_HOUR`,
  `NIGHT_END_HOUR`) are constants at the top of `scripts/pir_manager.py`; see the README for the
  full state table.

## Raspberry Pi Zero 2 WH: used pins

GPIO numbers in the code are always **BCM numbering** (`GPIO.setmode(GPIO.BCM)`), not physical
pin or WiringPi numbers.

| Function | BCM | Physical pin | Code constant |
|---|---|---|---|
| PIR sensor (RCW-0506) output | GPIO18 | 12 | `PIR_PIN` |
| Power switch module control input (display 5V) | GPIO17 | 11 | `DISPLAY_POWER_PIN` |
| 5V | – | 2, 4 | – |
| 3.3V | – | 1, 17 | – |
| GND | – | 6, 9, 14, 20, 25, 30, 34, 39 | – |

Avoid these for new connections: BCM0/1 (ID EEPROM), BCM2/3 (I2C, fixed 1.8 kOhm pull-ups),
BCM7-11 (SPI0), BCM14/15 (UART).

```bash
# State of all GPIOs / the two used pins
pinctrl
pinctrl get 17,18

# Header pinout on the Pi itself
pinout
```

## Current screen brightness (time-of-day schedule)

The schedule lives in `configuration.yaml` under `viewer.brightness_schedule` (list of
`time`/`value` pairs, `value` 0.0-1.0). It only dims the rendered image, not the black
mat/border, and is re-checked every 30 s.

```bash
# Configured schedule
grep -A12 "brightness_schedule:" ~/picframe/configuration.yaml

# When which value was applied (logged on every change, needs log_level INFO or lower)
grep "Applying scheduled brightness" ~/picframe/picframe.log* | tail -10

# Current brightness of the running picframe (HTTP interface, port from configuration.yaml)
curl -s "http://localhost:9000/?brightness="

# Set brightness manually for a quick visual test
curl -s "http://localhost:9000/?brightness=0.5"

# All values the HTTP interface currently exposes
curl -s "http://localhost:9000/?all"
```

> While a schedule is configured, a manually set brightness is reset to the scheduled value
> within 30 s. To test a value for longer, temporarily change the schedule instead (requires a
> `picframe.service` restart).
