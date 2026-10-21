# Picframe Development History

This document tracks the technical evolution, challenges, and key decisions made during the development of this Picframe fork.

## Video Support Development Status

This section documents the various attempts to implement robust video playback in `picframe`. It is intended to help community members understand the challenges and contribute to solutions.

### Development History

| Option | APIs/Tools Used | Status/Result | Reason for Failure / Disadvantage |
|:---|:---|:---|:---|
| **Direct OpenGL Rendering** | `OpenGL`, `pi3d` | Abandoned | Would require a **fundamental rewrite** of the `pi3d`-based rendering engine, which is too complex and time-consuming. |
| **1. `ffplay` Integration** | `ffplay`, `pi3d`, `os` | Abandoned / Rejected | The approach was rejected in favor of **VLC**, which was considered a more robust and better integrable player. Later attempts with `ffplay` showed the **same issues as with `vlc`**: it acts as an external player that takes over the screen and hangs at the end. |
| **2. VLC Integration** | `vlc`, `pi3d`, `os` | Partially functional / Abandoned | **Playback:** Robust. **Drawback:** Requires restarting `picframe` to switch back to images. Hangs at the end of the video. **Technical Reason:** `vlc` starts as a standalone process and **takes exclusive control of the display layer/screen context**. Upon exiting, it does not restore the previous graphics state, preventing the `pi3d`/OpenGL context from seamlessly taking over. The `pi3d` display must be completely re-initialized (equivalent to restarting `picframe`). Also, a visible console and blinking cursor appear during the transition. |
| **3. `ffplay` Analysis** | `ffplay` | Provides valuable information. | Only an **analysis tool**, not intended for direct integration into the application for playback. |
| **`mplayer` Integration** | `mplayer`, `pi3d`, `os` | Abandoned | Fails to initialize video driver and cannot open X11 display. |
| **9. `mpv` as External Player** | `mpv`, `pi3d`, `os`, `subprocess` | **Current & Successful Approach** | **Playback:** Robust, exits cleanly, and seamlessly switches between images and videos without performance issues. Console visibility is minimal during transitions. **Disadvantage:** Still requires clean shutdown and restart of the `pi3d` context for every video change. Complexity in the clean re-initialization of `pi3d` without restarting the whole service. |
| **8. Restarting `pi3d` for Videos** | `pi3d`, `subprocess` | **Abandoned** | **Plan:** Cleanly shut down `pi3d` before video playback, play video with external player (`mpv`), and re-initialize `pi3d` in-process. **Result:** This approach proved to be highly unstable. Multiple attempts resulted in either `AssertionError` crashes or a white screen, indicating a fundamental synchronization issue between the GPU and CPU when re-initializing the `pi3d` context. |
| **7. Restarting `picframe` Service** | `systemd`, `bash`, `python` | **Final & Stable Solution** | **Method:** After playing a video, the `picframe` application exits with a special code. A `watcher.sh` script, managed by `systemd`, detects this code and immediately restarts the application. A state file (`shown_albums.log`) ensures that playback resumes at the correct file. **Advantage:** This completely avoids the unstable `pi3d` re-initialization by creating a fresh process, ensuring maximum stability. |
| **`ffmpeg` Frame Streaming** | `ffmpeg`, `pi3d`, `numpy` | Abandoned | This method gives `pi3d` full control by streaming frames as textures. While offering seamless integration, it proved **too complex and unreliable** due to driver/compatibility and performance issues. |
| &nbsp;&nbsp;*4. Attempt 1: HW Decoding* | `ffmpeg` (`h264_v4l2m2m`) | Failed | `ffmpeg` reported "**Invalid data found when processing input**". This indicates a driver or compatibility issue with the `v4l2m2m` hardware decoder on the target system. |
| &nbsp;&nbsp;*5. Attempt 2: SW Decoding (to `rgb24`)* | `ffmpeg`, `pi3d`, `numpy` | Failed | `ffmpeg` process crashed with a "**Segmentation Fault**". The high memory consumption and data bandwidth required for the uncompressed `rgb24` format likely caused the crash. |
| &nbsp;&nbsp;*6. Attempt 3: SW Decoding (to `yuv420p`)* | `ffmpeg`, `pi3d`, `numpy` | Failed | While the `pi3d` texture loading issues were resolved in the test script, the overall approach remains **too fragile**. Final tests resulted in a **black screen**, and the complexity of debugging the `ffmpeg` pipeline outweighs the potential benefits compared to using a stable external player like `mpv`. |

### Hiding Console on HDMI during Video-Image Transition

| Attempt No. | Method | Goal | Result | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `dd` with large block (`bs=...`) | Fill screen with a color before/after video. | `[Errno 32] Broken pipe`, grey bar at the top edge. | ❌ Failed |
| 2 | `dd` as stream (without `bs`) | Bypass `BrokenPipeError`. | Worked before the video, but `BrokenPipeError` occurred after the video. | ❌ Failed |
| 3 | `dd` with temporary file in `/dev/shm` | Bypass `BrokenPipeError` after the video. | `KeyError: 'RGBA'` due to incorrect use of `img.save()`. | ❌ Failed |
| 4 | `dd` with correct temporary file | Fix `KeyError`. | `dd` failed with `exit status 1`. | ❌ Failed |
| 5 | `dd` with option `conv=notrunc` | Make `dd` more robust. | `dd` continued to fail with `exit status 1`. | ❌ Failed |
| 6 | Python `open()` instead of `dd` | Bypass `dd` errors. | `[Errno 28] No space left on device` when writing to `/dev/shm`. | ❌ Failed |
| 7 | Direct writing to `/dev/fb0` with Python | Bypass temporary file and space errors. | `[Errno 28] No space left on device` (likely a pipe issue). | ❌ Failed |
| 8 | **Radical Simplification** | Remove all manual coloring attempts and rely on `pi3d` restart. | All errors resolved. Transition is the normal, visible console. | ✅ Stable, but cosmetically not ideal |
| 9 | `setterm` in `watcher.sh` | Match black console to `pi3d` background color. | Worked initially, but caused issues after a system reboot. | ❌ Not reliable |
| 10 | **Return to Stable Solution** | Remove `setterm` commands. | Restoration of the stable state from Attempt 8. | ✅ Stable, but cosmetically not ideal |
| 11 | `dd if=/dev/zero` in `viewer_display.py` | Turn console black before/after video to hide text. | `dd` fails, but the side effect is a black screen covering the console. | ✅ **Working Feature** |

## Ken Burns Optimization History

The goal was to prevent wasting picture area by ensuring that scaling for the Ken Burns effect does not crop more than necessary for panning, scrolling, and scaling.

### Solution Attempts and Results

| Step | Change | Goal | Result / Side Effect | Cause |
| :--- | :--- | :--- | :--- | :--- |
| **GitHub** | `scale = base / zoom`<br>`offset = 0.5 - shift` | Original Logic | **Works (in original)** | The original logic is self-consistent but uses "camera shift" (minus). Changing only parts of it breaks consistency. |
| **1** | `scale = base / kb_scale` | Calculate Zoom | **Tiling** | In our adaptation, a Scale > 1.0 (due to incorrect base calculation) caused texture repetition. |
| **2** | `scale = view_w` (Value < 1.0) | Fix Tiling | **Distortion / Wrong Pos.** | Scaling was correct (Zoom), but the offset formula did not match the new scaling logic. |
| **3** | `scale = 1.0 / view_w` | Correct Zoom? | **3x Tiling** | Return to the error of Step 1. A small `view_w` (0.3) inverted leads to Scale 3.3 -> Tiling. |
| **4** | `offset = 0.5 - shift` | Positioning | **Inverted Movement** | "Scrolling starts at wrong position". The minus (from GitHub logic) did not match our definition of "Start Point". |
| **Fix** | `scale = view_w`<br>`offset = 0.5 + shift` | Correction | **Correct** | `view_w` (< 1.0) defines the viewport. `+ shift` moves the viewport intuitively in the positive coordinate direction (Start top -> End bottom). |
| **14** | **Geometry Scaling:** Switched from shader-based scaling to resizing the sprite geometry. | Eliminate vertical stripes caused by shader precision issues with `scale < 1.0`. | Stripes disappeared. However, image appeared as "rushing patterns" (pixel mush). | Coordinates became astronomically large due to incorrect aspect ratio calculations. |
| **15** | **Debug Logs:** Added logs for viewport and sprite dimensions. | Diagnose the cause of the pixel mush. | Logs revealed absurdly large viewport dimensions (e.g., width 196,560 pixels). | `viewport_aspect_ratio` was interpreted as ~182.0 instead of ~1.5. |
| **16** | **Sanity Check (Viewport):** Added sanity checks for aspect ratios. | Prevent application crashes or huge viewports. | Prevented huge viewports. Reset AR to default (16:9), causing aspect ratio mismatches (image wider than viewport). | Configuration values were still being parsed incorrectly, triggering the fallback. |
| **17** | **Portrait Optimization:** Implemented wobble reserve and virtual crop logic. | Enable correct scrolling for portrait images. | Portrait scrolling logic implemented, but vertical scrolling was stuck (`max_y=0`). | `portrait_crop_to_aspect_ratio` was parsed as ~123.0, resulting in zero scrollable area. |
| **18** | **Extended Debug Logs:** Added logs for `Final AR`. | Identify the exact values being parsed from config. | Confirmed `screen_aspect_ratio` parsed as `969.0` and `viewport_aspect_ratio` as `182.0`. | YAML 1.1 parser interprets `XX:YY` as base-60 (sexagesimal) integers. |
| **19** | **Sanity Check (Crops):** Added sanity checks for crop aspect ratios. | Make code robust against bad config values. | Code handled bad config gracefully (ignored crop), but behavior was still not as configured. | Root cause (YAML parsing) still present. |
| **20** | **Configuration Fix:** Added quotation marks to aspect ratios in `configuration.yaml` (e.g., `"16:9"`). | Force YAML to interpret values as strings. | **Success.** Correct ARs loaded. Display and scrolling work perfectly. | The "Sexagesimal" feature of YAML 1.1 (fixed by quotes). |
| **21** | **Code Cleanup:** Removed temporary debug logs. | Clean up code for production. | Code clean and stable. | - |
| **22** | **Re-enable Debug Logs:** Added persistent debug logs (Mode, Scroll Position). | Allow future debugging via log level change. | Detailed logs available for debugging (hidden in INFO/ERROR levels). | - |
| **23** | **Two-Sprite System:** Implemented separate sprites for background (outgoing) and foreground (incoming) images. | Fix "jumping" artifacts where the old image snapped to the new image's position during transition. | **Smoother Transitions.** Images now move independently. However, "Z-fighting" (flickering) occurred where images overlapped. | Single sprite geometry was shared/overwritten. |
| **24** | **Z-Separation & Freeze:** Placed background sprite at `z=10.0` and foreground at `z=5.0`. Stopped animating background during fade. | Eliminate flickering and reduce calculation load. | **Stable Transitions.** No flickering. Old image pauses while new one fades in. | - |
| **25** | **Landscape Pan Correction:** Extended random pan range from `0.0..1.0` to `-1.0..1.0`. | Fix issue where landscape images were always shifted to the right (left edge pinned). | **Centered Movement.** Images now pan in all directions. | Previous logic assumed positive offset only. |
| **26** | **Targeted Landscape Zoom:** Defined explicit start/end points (Center $\leftrightarrow$ Zoom/Wobble). | Ensure images start or end perfectly centered/fullscreen without black bars. | **Cinematic Look.** Zoom In starts full; Zoom Out ends full. | - |
| **27** | **Ghosting Fix:** Changed background sprite alpha to `1.0 - smooth_alpha` (cross-fade). | Prevent old image from showing through transparent borders of the new image (aspect ratio mismatch). | **Clean Cut.** Old image disappears completely as new one appears. | Previous logic kept background opaque (`alpha=1.0`) behind the blending foreground. |
| **28** | **Performance Optimization:** Added image downscaling in `__tex_load` before GPU upload. | Reduce RAM usage and IO wait (swapping) on Raspberry Pi Zero 2. | **Better Performance.** Reduced lag. However, portrait images became blurry. | Naive scaling to display height reduced resolution too much for "Fit Width" portrait images. |
| **29** | **Smart Downscaling:** Calculated target resolution based on Viewport and Aspect Ratio (Fit Width vs Fit Height). | Maintain sharpness for all aspect ratios while optimizing memory. | **High Quality & Performance.** Portrait images are sharp, memory usage remains low. | - |
| **30** | **Timer Logic Fix**<br>Reset display timer *after* image load. | Prevent images from being skipped or shown too briefly when loading takes time (IO wait). | **Correct Display Time**<br>Images stay for the configured `time_delay` regardless of loading speed. | Previous logic started timer at load start; heavy images consumed the display time while loading. |
| **31** | **Time-based Transitions**<br>Decoupled fade progress from framerate. | Ensure transitions take exactly `fade_time` seconds, even if FPS drops to <1 during background loading. | **Constant Transition Speed**<br>No more "slow motion" transitions during high load. | Previous frame-based logic slowed down transitions when CPU was busy. |
| **32** | **Late Timestamping**<br>Capture transition start time *after* GPU texture upload. | Fix "jumping" transitions where the fade was mathematically over before the first frame was drawn. | **Smooth Start**<br>Transition starts at 0% alpha exactly when the image appears. | Texture upload caused a delay that was counted as part of the transition time. |
| **33 | **Pre-emptive GC**<br>Force `gc.collect()` before transition starts. | Move inevitable memory cleanup freezes to the invisible loading phase. | **Fluid Animation**<br>Eliminates stuttering during the visible fade effect. | Python's GC would otherwise run randomly during the animation. |
| **34** | **Panorama Mode**<br>Added dedicated logic for ultra-wide images (`AR > Screen AR`). | Enable horizontal scrolling for panoramas instead of just zooming. | **New Feature**<br>Panoramas scroll left/right; standard landscapes zoom in/out. | - |

## Display Power Control: CEC vs. GPIO Hard-Switch

**Problem:** The initial test setup used a Sony TV, which correctly turns off its backlight on
HDMI-CEC standby (`echo 'standby 0' | cec-client -s -d 1`). After switching to the final hardware
— a Verbatim portable FHD display (#49593) — CEC standby over HDMI no longer turns off the
backlight; the display stays lit.

**Solution:** Hard-switch the display's 5V power supply using a MOSFET module (XY-MOS) driven by
a Raspberry Pi Zero 2 WH GPIO pin.

**Pitfall — pin numbering scheme mismatch:** The wiring was originally planned on a compact 2x5
(10-pin) header breakout, using BCM4 (physical pin 7) for the PIR sensor and BCM8 (physical pin
24, SPI0 CE0) for the MOSFET trigger. During wiring, a pi4j reference table using **WiringPi
numbering** (not BCM) was mistakenly consulted for the MOSFET pin: WiringPi pin 7 happens to equal
physical pin 7 (= BCM4, correct by coincidence of numbers), but **WiringPi pin 8 equals physical
pin 3**, not physical pin 24. Physical pin 3 is BCM2 (I2C1 SDA), a special-function pin with a
permanent hardware pull-up to 3.3V — unsuitable as a generic switched output, and a status LED
observed lit on the module while wired there was not reliable evidence of trigger polarity, since
that pin idles HIGH regardless of software due to its fixed I2C pull-up.

**Final pin assignment:** The compact 10-pin header was replaced with a larger header breakout,
removing the pin-availability constraint. Final wiring (BCM numbering, matching
`GPIO.setmode(GPIO.BCM)` used throughout the code):
*   **PIR sensor (RCW-0506):** BCM18 (physical pin 12) — `PIR_PIN` in `pir_manager.py` / `test_pir.py`.
*   **MOSFET trigger (display 5V switch):** BCM17 (physical pin 11) — `DISPLAY_POWER_PIN`.

Both are plain general-purpose GPIOs with no special/hybrid function (not I2C, SPI, UART, or
EEPROM-ID pins), so no fixed pull-up or kernel driver conflicts apply.

**Implementation:** `pir_manager.py` and `test_pir.py` support both display power methods via
constants:
*   `DISPLAY_POWER_METHOD`: `"cec"` (original, HDMI-CEC via `cec-client`) or `"gpio"` (new, hard
    5V switch via `DISPLAY_POWER_PIN`). Kept configurable so the CEC path remains available as a
    fallback (e.g. for testing against a CEC-compliant TV again).
*   `DISPLAY_POWER_ACTIVE_HIGH`: Trigger polarity of the MOSFET module's control pin. Defaults to
    `True` (GPIO HIGH = display on); flip to `False` if the module inverts. Must be verified with
    `test_pir.py` on the actual hardware, since it was not reliably determined during the pin
    mix-up described above.

**Open items to verify on hardware:**
*   Confirm the XY-MOS module's actual trigger polarity (active-HIGH vs. active-LOW) and adjust
    `DISPLAY_POWER_ACTIVE_HIGH` if needed.
*   `RPi.GPIO`'s `GPIO.cleanup()` (called on script exit) resets `DISPLAY_POWER_PIN` to a floating
    input, which can leave the MOSFET gate undriven during a crash/restart window. If this causes
    visible flicker, add a physical pull resistor on the gate matching the desired fail-safe state.

**Follow-up — night override removed:** After testing the GPIO hard-switch on the real hardware,
`pir_manager.py`'s "night override" (motion during the night window would wake the frame and keep
WiFi/display on until morning) was removed entirely. Night mode (23:00–06:00) is now unconditional:
WiFi stays blocked and the PIR sensor is ignored the whole window, including if the script itself
(re)starts during that time (previously it would briefly unblock WiFi/turn everything on at
startup before the next loop tick re-evaluated day/night). See README's "Logic of `pir_manager.py`"
section for the current state table.

## Time-of-Day Brightness Dimming

**Problem:** The portable HDMI displays used here (even the more expensive ones) have no
ambient-light sensor and no programmatically reachable backlight control — the backlight
electronics live entirely inside the monitor and aren't exposed over HDMI or CEC (no standard CEC
opcode for brightness; vendor-specific extensions exist on some smart TVs but not on generic
portable monitors). Wanted: a first test of a time-of-day-based brightness reduction, to see
visually how much dimming the rendered image needs before considering anything more elaborate
(e.g. an ambient light sensor).

**Options considered:**
1.  **App-level (chosen):** `viewer_display.py` already had an unused `set_brightness()`/
    `get_brightness()` pair driving a shader uniform (`Shape.unif[55]`, multiplies
    `gl_FragColor.rgb` in `blend_new.fs`) — built for MQTT/Home Assistant control originally, but
    unreachable because `Controller` was missing the `brightness` property that forwards to it
    (one of the wrapper methods dropped during the video-restart refactor, see `TODO.md`). The
    multiplier only applies to `__slide` (the image content), not `__slide_bg` (the mat/background,
    drawn with a separate flat shader) — so the black letterbox/pillarbox borders (intentionally
    covered later by a physical cardboard mat) are never touched, which is exactly what's wanted.
2.  **DRM/KMS gamma LUT or CTM (rejected for now):** setting a CRTC gamma/color-transform property
    on `/dev/dri/card0` would dim the entire HDMI output (not just picframe's content) without a
    modeset — so no visible resync/black-flash is expected from the property change itself, unlike
    a resolution/refresh-rate change. Rejected anyway because `pi3d`'s own KMS rendering already
    holds DRM master; a *separate* process (e.g. `pir_manager.py`) trying to set CRTC properties
    from outside would very likely get `EACCES`. Doing it from within the `picframe` process itself
    would work, but that just reduces to option 1's architecture with a different (harder to debug)
    mechanism, for no benefit here since only picframe's own content needs dimming.

**Implementation:** added `brightness` property to `controller.py` (fixes that one item from the
missing-wrapper bug, the other ~14 are still open, see `TODO.md`), plus a `viewer.brightness_schedule`
config list (`[{time: "HH:MM", value: 0.0-1.0}, ...]`, empty = disabled) that `Controller.loop()`
checks every 30s and applies via the new property. Purely additive — no effect unless configured.

## TTY Color Change Attempts

*   **Objective:** Permanently change the **background color** of the entire local **Console (TTY1) on Raspberry Pi OS Bookworm Lite** (HDMI display) from **Black to Grey**.
*   **Requirement 1:** The **login prompt** and last boot messages must be made **invisible** (Foreground color = Background color).
*   **Requirement 2:** Remote **SSH shells** must **not** be affected (must retain default colors).
*   **Constraint:** The color change must be **permanent** and visible **before the login prompt**.

### Solution Attempts and Results

| Attempt | Method & Commands | Target/Location of Change | Result | Reason for Failure (if applicable) |
| :--- | :--- | :--- | :--- | :--- |
| **1** | `setterm` & ANSI Palette Codes | `~/.bashrc` (After login only) | **Unsuccessful** | Executes only after login; only changes lines actively written to. |
| **2** | Separate Systemd Service (Timing Issue) | `/etc/systemd/system/` (`Before=getty.target`) | **Unsuccessful** | Command executes too early and is immediately overridden by TTY initialization. |
| **3** | TTY Initialization Modification via `getty` Drop-in (`ExecStartPre`) | `/etc/systemd/system/getty@tty1.service.d/` | **Unsuccessful** | Color is reset by `agetty` or the Framebuffer right before the prompt is displayed. |
| **4** | Kernel Palette Override (`COLOR_MAP`) | `/etc/default/console-setup` (with `update-initramfs`) | **Unsuccessful** | Kernel/Graphics firmware reloads default colors after `initramfs` stage. |
| **5** | **Partial Success** (Delayed Systemd Service) | `/etc/systemd/system/tty-color-fix.service` (`After=getty.target`, `sleep 2`) | **Partially Successful** | **Background** permanently Grey. Last log lines/prompt are visible and scrolled up. |
| **6** | **Final Solution** (Aggressive Scrolling) | `tty-color-fix.service` (`sleep 2` + `setterm -clear` + **50 invisible newlines**) | **Successful** | **Entire screen** is Grey/Blank. Unwanted text is pushed out of the visible viewport. |

## New Task: Video Integration as External Preprocessing Process

Our goal is to seamlessly integrate videos as a series of cross-faded still images into the slideshow without compromising the stability of `picframe`. After direct integration attempts failed, we are now pursuing a more robust, external approach (the "Postman Approach").

**Core Principle:** Strict separation of concerns.
*   `picframe` is solely responsible for displaying **images**.
*   A new, separate process is responsible for converting **videos to images**.

**The Procedure in Key Points:**

1.  **Clean up `picframe`:**
    *   All code changes related to the direct processing of videos (e.g., `.mp4`, `.mov`) will be removed from the `picframe` core (specifically from `image_cache.py`, `controller.py`, `viewer_display.py`).
    *   `picframe` will be made "video-blind". It will only recognize and process image files like `.jpg`, `.png`, etc.

2.  **New, External Script (`video_preprocessor.py`):**
    *   This script will run as a standalone process in the background (e.g., via a `cronjob` or its own `systemd` service).
    *   **Task 1: Find Videos:** The script searches the image directories (`pic_dir`) for video files.
    *   **Task 2: Extract Frames:** For each found video that has not yet been processed, it calls `ffmpeg`.
    *   **Task 3: Save Images:** It extracts a single frame from the video at regular intervals (e.g., every 10 seconds) and saves it as a `.jpg` file in a dedicated subfolder (e.g., `MyVacation.mp4_frames/`).
    *   **Task 4: Avoid Repetition:** The script remembers which videos have already been processed to avoid duplication (e.g., by checking if the `_frames` folder already exists).

3.  **Integration into the Slideshow:**
    *   The running `picframe` process notices through its `ImageCache` mechanism that a new folder with new images has appeared.
    *   It treats these extracted frames like normal photos, adds them to its database, and includes them in the slideshow rotation.

**Advantages of this Approach:**
*   **Stability:** The `picframe` process is never disturbed by `ffmpeg` calls. The `pi3d` startup conflict is completely avoided.
*   **Performance:** The computationally intensive video conversion can run with low priority in the background and minimally affects the smooth display of the slideshow.
*   **Simplicity:** We use the existing, robust functionality of `picframe` to detect new files instead of integrating complex new logic into the core.

### History of Implementation Attempts

Here is a table summarizing our previous attempts and the reasons for their failure.

| Attempt No. | Approach | Implementation Idea | Reason for Failure |
| :--- | :--- | :--- | :--- |
| 1 | **Direct Integration** | The `ImageCache` was supposed to read metadata from videos (`Duration`, `Resolution`) using `ffprobe` while scanning files and save it in the database. | **Race Condition at Startup:** The `ImageCache` thread started `ffprobe` (a `subprocess`) *before* `pi3d` in `start.py` could initialize the display. This `subprocess` interfered with the graphics subsystem and led to an immediate crash (`... has no attribute 'context'`). |
| 2 | **"Just-in-Time" Approach** | The `ImageCache` was supposed to only detect videos but not read metadata. Only when a video is up next, the `Viewer` should call `ffprobe` to determine the duration and then extract the frames. | **Still Startup Conflict:** Although the logic was moved, the `import` statements for `subprocess` and the associated functions were still present in the code. Merely loading these modules at startup seemed sufficient to disrupt the `pi3d` initialization process on the Pi Zero. We never got to actually test the "Just-in-Time" logic. |
| 3 | **Optimization of Start Order** | We restructured `start.py` so that `pi3d.Display.create()` is executed as the very first step, even before logging and the creation of the `Model` object (and thus the `ImageCache` thread). | **Import-Time Conflicts:** Even with the correct order, the start failed. The cause was that `start.py` had to import `viewer_display.py`. This file in turn imported `subprocess`. The `import` process itself, even before a function is called, created the conflict. |
| 4 | **Complete Cleanup** | We tried to remove all video-related changes from all files (`image_cache`, `controller`, `viewer_display`, `get_image_meta`, `start`) to return to a stable state. | **Overlooked Code Remnants:** During manual cleanup, individual lines introduced by us (like a hardcoded `self.__use_sdl2 = False`) or incorrect import orders remained in the files, which continued to prevent startup and led to slightly different but essentially the same error messages. |

**Summary Finding:** Any form of `subprocess` calls or even their `import` preparation within the main `picframe` process is too unstable on the target hardware (Pi Zero) and leads to an unrecoverable conflict with the `pi3d` graphics initialization. Decoupling into a completely separate process is therefore the only logical and promising next step.


## Optimization of Video Slideshow on Raspberry Pi Zero 2

Seamlessly integrating videos as a "slideshow" (frame extraction instead of video player) presents a challenge on hardware with limited RAM (512 MB) and limited I/O bandwidth. The following measures were necessary to achieve smooth playback without stuttering and without system crashes (OOM/Swap).

### Key Findings

*   **I/O Bottleneck:** Simultaneous writing of extracted frames by `ffmpeg` and reading by `pi3d` immediately overloads the SD card. This leads to high `IO-Wait`, blocking the display.
*   **RAM Bottleneck:** Since GPU and CPU share memory, too many buffered images or inefficient memory management immediately lead to swapping to the SD card (`kswapd0`), which extremely slows down the system.
*   **Solution:** A combination of strict process prioritization, hardware decoding, and offloading the write load to a separate medium.

### Optimization Measures

| Area | Measure / Command | Effect |
| :--- | :--- | :--- |
| **Decoding** | `ffmpeg -c:v h264_v4l2m2m` | Uses the Pi's hardware video unit. Massively relieves the CPU for rendering. |
| **I/O Priority** | `ionice -c 3` | Sets `ffmpeg` to "Idle" priority. It is only allowed to write when no other process (like the slideshow) is accessing the disk. |
| **CPU Priority** | `nice -n 19` | Gives `ffmpeg` the lowest CPU priority so that the UI (`pi3d`) always remains smooth. |
| **Memory** | `pi3d.Texture(..., free_after_load=True)` | Deletes image data from RAM as soon as it has been uploaded to the GPU. Prevents RAM overflow. |
| **Throttling** | `SIGSTOP` / `SIGCONT` | The script monitors the buffer. If >5 frames are pre-produced, `ffmpeg` is hard paused to free up I/O and RAM cache. |
| **Quality** | `ffmpeg -q:v 6` | Reduced JPEG quality significantly decreases file size and thus write load, without visible artifacts on the display. |
| **Scaling** | `flags=bilinear` | Bilinear scaling is significantly faster than bicubic on the Pi Zero. |
| **Hardware** | **USB Stick (ext4)** | **Crucial:** Offloading the temp directory to a USB stick decouples the write load from the system SD card. |

### Recommended Setup for Pi Zero 2

To operate the video slideshow stably, it is strongly recommended to use a USB stick for temporary files:

1.  Format USB stick with `ext4` (faster/less CPU load than FAT32).
2.  Mount under e.g., `/mnt/usb`.
3.  Configuration/Call with `--temp-dir /mnt/usb`.

## Sync Deadlock: "No Pictures" After All Server Albums Were Shown (2026-10)

**Symptom:** After several weeks of the extended hardware test, the frame only showed the "no pictures" image, although the SMB server was reachable. `sync.log` showed every run mounting the share, logging `Starting sync loop...` and then nothing for 30 minutes, until the next cron run unmounted the share underneath it (`Mount point ... already in use. Unmounting`, `find: ... No such file or directory`).

**Analysis:**

| Finding | Cause | Effect |
| :--- | :--- | :--- |
| Endless sync loop | Album selection was unbounded random rejection sampling (random year → random album → skip if shown/cached). ~741 of ~764 server albums were already in `shown_albums.log`. | No album downloaded; loop only ended when the next run unmounted the share. |
| Deadlock | `shown_albums.log` was only reset by `model.py` ("All albums shown"), and only when the *local cache* still contained albums. With `delete_after_show`, the cache was empty, so picframe never reset it, while sync waited for unshown albums that did not exist. | Permanent "no pictures". |
| Parallel runs | No lock; cron runs (and `model.py`'s initial-sync `Popen`) unmounted each other's share. | Aborted runs, orphaned `<album>.tmp` folders. |
| Orphaned `.tmp` / media-less album folders | `set -e` abort mid-copy (e.g. WiFi blocked at 23:00); folders ignored by picframe but counted in the quota or blocking the album name. | Quota can fill up with invisible files. |
| Image paths in `shown_albums.log` | The resume bookmark (last line) was only replaced if the file still existed — but `delete_after_show` had just deleted it, so every shown image stayed in the log. | Log grew by one line per image; image lines were loaded as "albums". |
| Log sorted alphabetically | `__write_shown_albums_log()` rewrote the whole file with `sorted()` on every album change (and would also have overwritten any reset done by sync). | Playback order lost. |

**Final solution:**

*   **`sync_photos.sh`:**
    *   Builds the full album list of the share (`<year>/<album>`, hidden and `@...` NAS folders ignored), subtracts albums listed in `shown_albums.log` and albums already in the cache, and downloads from a shuffled candidate list. The loop always terminates.
    *   Albums without matching media files are appended to `shown_albums.log` so they no longer block a round (checked again next round).
    *   **New round:** if every album of the share is listed in the log, the share's entries are removed from it (backup `shown_albums.log.<date>.bak`; entries of other shares are kept). The decision is based on *server albums minus shown*, so stale entries of deleted/renamed folders never block a reset, and unshown albums still in the cache prevent a premature reset.
    *   Single instance via `flock` on `/dev/shm/picframe_sync.lock`, acquired *before* the cleanup trap is installed (a second instance must not unmount the running instance's share).
    *   On start: removes orphaned `<album>.tmp` folders, album folders without media and empty year folders.
*   **`model.py`:**
    *   Resume bookmark moved to `~/picframe/resume_file.txt` (written by `save_current_file_state()`/`save_resume_state()`, so the video exit-code-10 restart keeps working).
    *   `shown_albums.log` is append-only (one album per line, playback order); it is re-read from disk on every playlist rebuild and before appending, so a new round started by sync takes effect immediately.
    *   picframe's own "all cached albums shown" case only replays the cached albums and no longer touches the log.
    *   One-time migration on start: image lines are removed from an old-format log, the old bookmark (last line) is moved to the resume file.

## SD Card Full: Kernel Log Flood from a Hung WiFi Chip (2026-10)

**Symptom:** `picframe.service` in a crash loop (restart counter > 2400), `OSError: [Errno 28] No space left on device`, `sqlite3.OperationalError: database or disk is full`, no usable `/tmp`. Before that: Pi not in WiFi, also during the day; only cold boots helped (early October and again from 2026-10-19).

**Analysis:**

| Step | Finding |
| :--- | :--- |
| `du` on `/` | `/var/log` = 47 GB: `kern.log` 23 GB + `syslog` 23 GB (rsyslog stores kernel messages twice). Journal only 516 MB (size-limited). picframe cache within quota (4.7 GB / 5 GB). |
| Most frequent message | 4679 of the last 5000 lines: `brcmfmac: brcmf_sdio_htclk: HT Avail request error: -110` — the driver can no longer reach the WiFi chip (BCM43436 via SDIO) and logs every retry. |
| First occurrence (rotated logs) | 2026-10-04 19:34 (uptime 26 days, = WiFi outage of early October) and 2026-10-16 14:01 (uptime 5 days); flood from 2026-10-18. Both started in the daytime, so the nightly `rfkill block` is **not** the trigger. |
| Suspects | WiFi power saving was on (`iw wlan0 get power_save` → `on`) — a known cause of hung chips on the Pi Zero 2 W. Under-voltage (`vcgencmd get_throttled` = `0x0`, but only covers the current boot). |

**Solution:**

*   **`pir_manager.py`:** New `set_wifi()` helper (rfkill + no-WLAN flag) that runs `iw wlan0 set power_save off` after every `rfkill unblock` and at startup (the driver re-enables power saving on chip re-initialization; retries while `wlan0` reappears). The nightly `rfkill block` is kept.
*   **`install.sh`, step 13 (safety net):** rsyslog filter `/etc/rsyslog.d/10-brcmfmac-flood.conf` drops the flood message (still in the size-limited journal); `maxsize 100M` in `/etc/logrotate.d/rsyslog`; `logrotate.timer` runs hourly instead of daily. Package `iw` added.
*   **Crontab:** Duplicate `rfkill block/unblock wifi` entries removed on the Pi (pir_manager does this).
*   **Open:** Watch whether disabling power save prevents further hangs. If not: WiFi watchdog in `pir_manager.py` (reload `brcmfmac` when the router is unreachable for minutes), and check the power supply under load (display switched on via the Pololu switch on the same 5V supply).
