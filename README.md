## PictureFrame powered by pi3d

![picframe logo](https://github.com/helgeerbe/picframe/wiki/images/Picframe_Logo.png)

- [PictureFrame powered by pi3d](#pictureframe-powered-by-pi3d)
- [What Is PictureFrame?](#what-is-pictureframe)
- [History of PictureFrame](#history-of-pictureframe)
- [Highlights of PictureFrame](#highlights-of-pictureframe)
- [Documentation](#documentation)
- [Acknowledgement](#acknowledgement)

## What Is PictureFrame?

This is a viewer for a raspberry powered picture frame. For remote control it provides an automatic integration into [Home Assistant](https://www.home-assistant.io/) via MQTT discovery.

- https://github.com/helgeerbe/picframe
- Paddy Gaunt, Jeff Godfrey, Helge Erbe
- Licence: MIT
- Tested on rasberry 3B+/4, Ubuntu 20.10 and Python 3.7

## History of PictureFrame

When I started 2019 my DIY project building a raspberry powered digital picture frame I came across Wolfgang's website [www.thedigitalpictureframe.com](https://www.thedigitalpictureframe.com/). I ran my frame with the [pi3d PictureFrame2020.py](https://github.com/pi3d/pi3d_demos) viewer, but always missed a more deeply integration to my smart home server running [Home Assistant](https://www.home-assistant.io/).As my personel corona project I decided to rewrite the viewer to my needs. Hoping  someone can make use of it.

## Highlights of PictureFrame

- Viewer
  - blend effects
  - auto mat generation
  - photo metadata overlays (title, location, date, ...)
  - live clock
  - automatic pairing of portrait images
  - keyboard, mouse and touch screen support
- Filter by
  - IPTC tags
  - location
  - directories
  - date
- Remote Control
  - control interface for mqtt, http(s)
  - tun on/off display
  - next/prev/pause image
  - shuffle play
  - toggle metadata overlays
  - toggle clock visibility
  - retrieve image meta info (exif, IPTC)

# Hardware

* Raspberry Pi Zero 2 WH
* 64 GB SD card for image cache, OS, and software
* Full-HD display
* Wooden picture frame, Maple
* PIR Motion Sensor HC-SR501 PIR

---

# Software

* Raspberry Pi OS Bookworm Lite (64-bit)
* Without desktop environment (headless, no Wayland/X11)
* PictureFrame with pi3d: [https://github.com/helgeerbe/picframe/tree/main](https://github.com/helgeerbe/picframe/tree/main) (Python environment)
    * Slideshow uses Pi3D directly on the framebuffer
    * Smooth cross-fading transition with separately adjustable delay for transition and display time
    * Permanent display of the time
    * Display of the album directory name **{Location}** and year directory name **{YYYY}** as well as any existing EXIF data of the respective photo
    * Playback of photos from a local, limited image cache on the SD card
* Remote access for maintenance, configuration, and updates
    * SSH Shell
    * WebUI
* Interfaces
    * Bluetooth of the Pi Zero 2 WH is permanently deactivated
    * WLAN of the Pi Zero 2 WH is deactivated at night between 11:00 PM and 6:00 AM

## Documentation

[Full documentation can be found at the project's wiki](https://github.com/helgeerbe/picframe/wiki).

Please note that PictureFrame may change significantly during its development.
Bug reports, comments, feature requests and fixes are most welcome!

To find out what's new or improved have a look at the [changelog](https://github.com/helgeerbe/picframe/wiki/Changelog).

## Acknowledgement

[glenvorel](https://github.com/glenvorel) Thanks for the new keyboard, mouse and touch screen support.

Many Thanks to Wolfgang [www.thedigitalpictureframe.com](https://www.thedigitalpictureframe.com/) for your inspiring work. 
A special Thank to Paddy Gaunt one of the authors of the [pi3d](https://github.com/pi3d/pi3d_demos) project. You are doing a great job!

Last but no least a big Thank You to Jeff Godfrey. Your auto mat feature and database driven cache is an outstanding piece of code.

---

## Fork Information

This repository is a fork of the original [picframe by helgeerbe](https://github.com/helgeerbe/picframe). It includes several modifications and new scripts to enhance functionality and automation.

### Key Changes in this Fork
*   **Advanced Scripting:** Introduction of several utility scripts for automation and maintenance (see [Utility Scripts](#utility-scripts) below).
*   **Enhanced Slideshow Features:**
    *   **Group by Folder (`group_by_dir`):** Displays all photos from one album before moving to the next.
    *   **Delete After Show (`delete_after_show`):** Option to permanently delete photos from the cache after they have been displayed.
*   **General stability improvements** and bug fixes throughout the application.

## Automatic Slideshow during the day 📅

* Slideshow and display are deactivated at night between **12:00 AM and 6:00 AM**.
* Detect with **PIR sensor RCW-0506** whether people are nearby.
* `pir_manager.py` checks PIR sensor for movement every 15 minutes:
    * **HOLD** (1h no movement): the slideshow is **paused**; as soon as movement is detected again, the slideshow resumes.
    * **PAUSED** (3h no movement): the slideshow is **paused** and the screen **turns black**. As soon as movement is detected again, it continues with the next image.
    * **OFF** (Night mode is activated between 12 AM and 6 AM): the `picframe` service is **terminated** and `kmsblank` is activated for 7 hours. **WLAN is off**. At 6 AM, the `picframe` service starts with a new album.

---

## Local Image Cache on SD card 🖼️

* Photos already shown are automatically **deleted** from the SD card by `picframe`.
* **Random or sequential playback** of photos within an album `{Location}` from the local cache `picframe_cache`
* **Random or sequential selection** of albums from different years `{YYYY}` from the local cache `picframe_cache`

---

## Photo Synchronization from Home Server (SMB) 💾

* `sync_photos.sh` runs **in the background** alongside the `picframe` service.
* Started regularly via **cron job**: synchronization from Windows photo share from server on the LAN via **SMB**.
* **Hourly check** during the day whether server share or IP is reachable only when WLAN is active.
* If the server is reachable: **automatic download** of photo albums until the cache is full.
* Directory structure of images on the server: `//{serverip}/{PhotoShare}/{YYYY}/{Location}`
    * Each album is assigned to a directory named `{Location}`.
    * Automatic download of albums/directories, each **randomly selected** for `{Location}` and `{YYYY}`.
    * Photo filenames usually follow `{YYYYMMDD_HHMMSS}{arbitrary suffix}.jpg` and may contain special characters, as far as allowed in the NTFS file system.
    * The **date and time stamp** of the files is transferred when copying from the server to `picframe_cache`.
* Maximum number of pictures per album is fixedly adjustable (`maxPicsPerAlbum`): if there are more photos in an album, e.g., only every 2nd, 3rd, or 10th photo in alphabetical order (ascending) is downloaded to the cache to avoid exceeding `maxPicsPerAlbum`.
* Cleaning up/deleting **empty folders** in `picframe_cache`.
* `sync_photos.sh` only fetches folders from the server that are **not noted** in `shown_albums.log`.

---

## System Scripts and Logging 🛠️

* `watcher.sh` is a **wrapper for picframe**; it starts `picframe` as a service after boot and runs in the background.
* `install.sh` **installs** all necessary packages and files required for Python, picframe, and additional shell scripts. `install.sh` also writes the necessary file for the `picframe` Linux service and writes the crontab entries. However, `install.sh` does not create the shell scripts themselves.
* `change.log` contains all **changes** to `picframe` and to added files, with the date and time of the change, grouped by days.
* `changes.txt` contains a continuously updated **functional description** of all files that were modified and added in `picframe`.

### Utility Scripts
This fork includes a collection of powerful scripts located in the `scripts/` directory to automate and manage the picture frame.

*   **`pir_manager.py`:** A robust script to control the display and picframe service based on motion detection (PIR sensor) and a day/night schedule. It uses `cec-client` for display power and direct HTTP calls to control the slideshow, removing the need for an MQTT broker for this functionality. It also allows overriding the night schedule if presence is detected.
*   **`sync_photos.sh`:** A sophisticated script to synchronize both photos and videos from separate SMB shares into a single, unified local cache. It manages separate storage quotas for each media type, prioritizes photo downloads, and only downloads videos when the photo quota is nearly full. The script is designed to continuously fill the cache without automatically deleting files.
*   **`check_pic_dates.sh`:** A maintenance script to validate and correct file dates for both images and videos. It compares file system dates with EXIF/metadata dates and can interactively (or automatically) fix inconsistencies, ensuring chronological accuracy.
*   **`create_test_images.sh`:** A utility to generate a set of test images. It converts PNGs to JPGs, burns image metadata (dimensions, color space) as a text overlay onto the image, and adds randomized, plausible EXIF data, including GPS coordinates. This is useful for testing the frame's display capabilities.

---

## Extension

* Extension of the `picframe` Python environment for additional functions
    * `group_by_dir: true` shows all photos from the same folder before moving to a new folder. If `shuffle: true` is set, only images within the same folder are shown randomly. Otherwise, the sorting specified by `sort_cols` is used.
    * `shuffle: False` is adjusted depending on `group_by_dir`.
    * `delete_after_show: true` each photo is permanently deleted immediately after it is shown to free up SD storage space and prevent multiple displays
    * The path of each shown album from `picframe_cache` is written to `shown_albums.log`.
    * Display format $\ge$ image format 16:9 $\ge$ 13:9 $\ge$ 4:3 $\ge$ 5:4,
* Extension of the Ken Burns effect, if `kenburns: true`
    * NO (image change only starts after scrolling/zoom ends) - Ken Burns to the next image already starts during the cross-fade
    * **All:** Independent of image format
        * NO (Fixed point always top left) - if `kenburns_random_pan: true` random sideways drift for each image, random $\le$ `kenburns_wobble_pct`
        * If `kenburns_random_pan: false` centered zoom without sideways drift
    * **Landscape:** If *image width $\ge$ height*
        * If `kenburns_zoom_direction: random` randomly for each image
            * `zoom: in` starts screen-filling
                * YES - Image is magnified
            * NO (starts screen-filling) - `zoom: out` starts oversized
                * Image is reduced
            * Zoom always follows percentage random $\le$ `kenburns_zoom_pct`
        * If `kenburns_zoom_direction: in, out` same for each image
            * Corresponding to `zoom: in` or `zoom: out`
            * Zoom percentage random = `kenburns_zoom_pct`
    * **Portrait:** If *image width $\le$ height*
        * NO (multiple images side by side) - Scrolling starts with image width scaled exactly to display width, image aspect ratio is maintained.
        * If `kenburns_scroll_direction: random` randomly for each image
            * YES - `scroll: top down` or `scroll: bottom up`
            * NO - vertical scrolling starts and ends with a random offset $\le$ `kenburns_portrait_border_pct`
        * If `kenburns_scroll_direction: up, down` same for each image
            * Corresponding to `scroll: down = top down` or `scroll: up = bottom up`
            * Vertical scrolling starts and ends with a random offset $\le$ `kenburns_portrait_border_pct`

## Video Support Development Status

This section documents the various attempts to implement robust video playback in `picframe`. It is intended to help community members understand the challenges and contribute to solutions.

### Video Player Comparison

This table summarizes the results of testing different command-line video players on the target system.

| Player | Result | Notes |
| :--- | :--- | :--- |
| **mpv** | Plays correctly, exits cleanly. | Shows some warnings on console (`[vo/sdl] Warning: this legacy VO has bad performance...`). Returns to console after playback. Seems to be the most promising candidate for integration. |
| **vlc** | Plays correctly, but hangs at the end. | Requires `Ctrl-C` to exit. Uses DRM Video Accel for hardware decoding. |
| **ffplay** | Plays correctly, but hangs at the end. | Last frame remains on screen. Requires `Ctrl-C` to exit. |
| **mplayer** | Fails to play. | Error: `vo: couldn't open the X11 display ()!`. Cannot initialize video driver. |

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
| &nbsp;&nbsp;*5. Attempt 2: SW Decoding (to `rgb24`)* | `ffmpeg`, `pi3d`, `numpy` | Failed | `ffmpeg` process crashed with a "**Segmentation Fault**" ("Speicherzugriffsfehler"). The high memory consumption and data bandwidth required for the uncompressed `rgb24` format likely caused the crash. |
| &nbsp;&nbsp;*6. Attempt 3: SW Decoding (to `yuv420p`)* | `ffmpeg`, `pi3d`, `numpy` | Failed | While the `pi3d` texture loading issues were resolved in the test script, the overall approach remains **too fragile**. Final tests resulted in a **black screen**, and the complexity of debugging the `ffmpeg` pipeline outweighs the potential benefits compared to using a stable external player like `mpv`. **Specific Issues:** a) `GL_LUMINANCE / GL_RED` constants not found. b) `pi3d.Texture` expected a 3D array but received 2D. c) The final correction (3D array) has not yet been tested with the current code. |

### Attribution
*   **Author of modifications:** Martin Schmalohr
*   **AI-assisted development:** Some of the scripts and modifications in this fork were developed with the assistance of Google's Gemini.
