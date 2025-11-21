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
*   **`test_bulk_video_player.py`:** A comprehensive test script to systematically evaluate video playback performance. It iterates through all videos in the `test/videos/` directory, playing each with `mpv` while capturing detailed logs. The script uses `ffprobe` for media metadata and reads system information to determine display capabilities. All results, including metrics like effective FPS and playback errors, are compiled into a summary Markdown table. It requires `sudo` to accurately read the display's refresh rate.
*   **`test_bulk_video_player.log`:** The main log file generated by `test_bulk_video_player.py`. It contains the display properties and aggregates the detailed `mpv` logs for each tested video, making it a crucial resource for debugging playback issues.

---


### How Media Playback and File Management Works

This document describes the logic of how `picframe` selects, plays, and manages images and videos from the cache. The behavior is primarily controlled by the configuration file (`configuration.yaml`) and the state file (`~/picframe/shown_albums.log`).

---

#### 1. Basic Playback Logic

The playback method primarily depends on the `group_by_dir` option.

*   **If `group_by_dir: false` (Default):**
    *   All media files in the main cache directory (`pic_dir`) are treated as a single, large playlist.
    *   If `shuffle: true`, the entire list is reshuffled on each run (or after `reshuffle_num` runs).
    *   If `shuffle: false`, the files are played sorted according to `sort_cols`.

*   **If `group_by_dir: true` (Album Mode):**
    *   Playback is organized into albums, where each subdirectory in the cache is considered an album.
    *   An album that is **not** yet listed in `shown_albums.log` is randomly selected.
    *   **`picframe` will play this one album completely before switching to the next.**
    *   If `shuffle: true`, the files *within* the current album are shuffled.
    *   If `shuffle: false`, the files *within* the album are sorted according to `sort_cols`.

---

#### 2. State Management with `shown_albums.log`

This file is the "memory" of `picframe` and has a dual function:

*   **Album Tracking:**
    *   Each line (except the last one) contains the path to an album that has already been played completely.
    *   When an album is finished, its path is added here. `picframe` will not select this album again until all other albums have also been shown.
    *   When all available albums are in the log file, the list is reset, and the cycle begins anew.

*   **Playback Bookmark (last line):**
    *   The **last line** of the file serves as a temporary bookmark and always contains a full file path.
    *   **For images:** After each image change, the path of the *currently displayed* image is saved here.
    *   **For videos:** Shortly *before* a video starts, the path of the image that is supposed to come *after* it is saved here.
    *   **Purpose:**
        1.  **Transparency:** You can check at any time which file is currently running.
        2.  **Crash Safety:** In the event of an unexpected crash, `picframe` knows which file to resume with on restart.
        3.  **Video Restart:** This is the key mechanism to seamlessly resume playback after the necessary restart for videos.

---

#### 3. Special Behavior for Videos

Stable video playback is achieved through a controlled restart of the application:

1.  **Detection:** `picframe` detects that the next file is a video.
2.  **Set Bookmark:** It calls `save_resume_state()` to write the path of the *next* file to the last line of `shown_albums.log`.
3.  **Play Video:** The external player `mpv` is started and plays the video in full-screen mode.
4.  **Exit with Signal:** After the video, `picframe` exits itself with the special **Exit Code 10**.
5.  **Restart by Watcher:** The `watcher.sh` service, which monitors `picframe`, detects exit code 10 and immediately restarts the application. All other exit codes would terminate the service.
6.  **Resumption:** On restart, `picframe` reads the bookmark from `shown_albums.log`, finds the corresponding file in the album's playlist, and resumes the slideshow exactly at that point.

---

#### 4. Dynamic Cache Management

*   **Adding Files:**
    *   A background process (`ImageCache`) continuously scans the cache directory for new files and adds their metadata to the internal database.
    *   These new files will appear in the slideshow the next time the playlist is reloaded. This happens:
        *   When the application starts.
        *   After an album has been completely played in `group_by_dir: true` mode.
        *   After the list has been run through according to `reshuffle_num` in `group_by_dir: false` mode.

*   **Deleting Files (`delete_after_show: true`):**
    *   When this option is active, a file is **permanently** deleted from the cache after it has been displayed.
    *   Immediately after deletion, a reload of the playlist is forced (`force_reload()`) to ensure the deleted file is not selected again and the playlist index remains correct.

*   **Manually Deleting Files from Cache:**
    *   If a file is deleted externally, the `ImageCache` process notices this and removes it from the database.
    *   Should `picframe` try to load a file that has already been deleted but is still in the current playlist, the `os.path.isfile()` check will fail. The file is skipped, and the slideshow seamlessly moves on to the next file.


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

Hiding Console on HDMI during Video-Image Transition

| Versuch Nr. | Methode | Ziel | Ergebnis | Status |
| :--- | :--- | :--- | :--- | :--- |
| 1 | `dd` mit großem Block (`bs=...`) | Bildschirm vor/nach Video mit einer Farbe füllen. | `[Errno 32] Broken pipe`, grauer Balken am oberen Rand. | ❌ Fehlgeschlagen |
| 2 | `dd` als Stream (ohne `bs`) | `BrokenPipeError` umgehen. | Funktionierte vor dem Video, aber `BrokenPipeError` trat nach dem Video auf. | ❌ Fehlgeschlagen |
| 3 | `dd` mit temporärer Datei in `/dev/shm` | `BrokenPipeError` nach dem Video umgehen. | `KeyError: 'RGBA'` durch falsche Verwendung von `img.save()`. | ❌ Fehlgeschlagen |
| 4 | `dd` mit korrekter temporärer Datei | `KeyError` beheben. | `dd` schlug mit `exit status 1` fehl. | ❌ Fehlgeschlagen |
| 5 | `dd` mit Option `conv=notrunc` | `dd` robuster machen. | `dd` schlug weiterhin mit `exit status 1` fehl. | ❌ Fehlgeschlagen |
| 6 | Python `open()` statt `dd` | `dd`-Fehler umgehen. | `[Errno 28] No space left on device` beim Schreiben in `/dev/shm`. | ❌ Fehlgeschlagen |
| 7 | Direktschreiben in `/dev/fb0` mit Python | Temporäre Datei und Speicherplatzfehler umgehen. | `[Errno 28] No space left on device` (wahrscheinlich ein Pipe-Problem). | ❌ Fehlgeschlagen |
| 8 | **Radikale Vereinfachung** | Alle manuellen Färbeversuche entfernen und auf den Neustart von `pi3d` vertrauen. | Alle Fehler behoben. Übergang ist die normale, sichtbare Konsole. | ✅ Stabil, aber kosmetisch nicht ideal |
| 9 | `setterm` in `watcher.sh` | Die schwarze Konsole an die `pi3d`-Hintergrundfarbe anpassen. | Funktionierte zunächst, verursachte aber Probleme nach einem System-Neustart. | ❌ Nicht zuverlässig |
| 10 | **Rückkehr zur stabilen Lösung** | `setterm`-Befehle entfernen. | Wiederherstellung des stabilen Zustands von Versuch 8. | ✅ Stabil, aber kosmetisch nicht ideal |
| 11 | `dd if=/dev/zero` in `viewer_display.py` | Konsole vor/nach Video schwarz schalten, um Text zu verbergen. | `dd` schlägt fehl, aber der Nebeneffekt ist ein schwarzer Bildschirm, der die Konsole verdeckt. | ✅ **Funktionierendes Feature** |

### Display Eigenschaften

- **Hersteller:** `Sony`
- **Modell:** `SONY TV`
- **Baujahr:** `2014`
- **DRM_Connector:** `HDMI-A-1`
- **Display:** `HDMI-A-1`
- **Auflösung:** `1920x1080`
- **Bildwiederholrate:** `50.00 Hz`

--- Testergebnisse für Sony KDL-32W705B ---
| Verzeichnis | Videodatei | Auflösung | Codec | Profile@Level | MP4/FPS | Dauer | Frames | Status | Laufzeit | Playback | Performance | MPV/FPS | Display/FPS | Details |
|-------------|------------|-----------|-------|---------------|---------|--------|--------|--------|----------|----------|-------------|---------|-------------|---------|
| ext | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.avi | 1280x720 | h264 | High@3.2 | 600.00 | 9.98s | 452 | OK | 15.18s | 9.99s | OK | 45.2 | 0.00 |  |
| ext | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.mkv | 1280x720 | h264 | High@3.2 | 50.00 | 0.00s | 452 | OK | 13.03s | 9.02s | OK | 50.1 | 0.00 |  |
| ext | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.mov | 1280x720 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.76s | 9.00s | OK | 50.2 | 0.00 |  |
| ext | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.91s | 8.99s | OK | 50.3 | 0.00 |  |
| ext | Super8.mp4 | 960x720 | h264 | High@3.1 | 18.00 | 19.11s | 344 | OK | 22.78s | 19.02s | OK | 18.1 | 0.00 |  |
| hd | 1280x720p25_2ch_libx264_high_yuv420p_gop50_bit2500k_max2500k_buf7M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | h264 | High@3.1 | 25.00 | 10.08s | 252 | OK | 14.34s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 1280x720p25_2ch_libx264_high_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | h264 | High@3.1 | 25.00 | 10.08s | 252 | OK | 13.96s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 1280x720p25_2ch_libx265_main_yuv420p_gop50_bit2500k_max2500k_buf7M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | hevc | Main@9.3 | 25.00 | 10.08s | 252 | OK | 14.03s | 10.21s | OK | 24.7 | 0.00 |  |
| hd | 1280x720p25_2ch_libx265_main_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | hevc | Main@9.3 | 25.00 | 10.08s | 252 | OK | 14.36s | 10.31s | OK | 24.4 | 0.00 |  |
| hd | 1280x720p50_2ch_libx264_high_yuv420p_gop100_bit3584k_max3584k_buf7M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 10.04s | 502 | OK | 13.81s | 10.03s | OK | 50.0 | 0.00 |  |
| hd | 1280x720p50_2ch_libx264_high_yuv420p_gop100_bit5M_max5M_buf10M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 10.04s | 502 | OK | 13.79s | 10.04s | OK | 50.0 | 0.00 |  |
| hd | 1280x720p50_2ch_libx265_main_yuv420p_gop100_bit3584k_max3584k_buf7M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | hevc | Main@12.0 | 50.00 | 10.04s | 502 | OK | 14.86s | 10.88s | OK | 46.1 | 0.00 |  |
| hd | 1280x720p50_2ch_libx265_main_yuv420p_gop100_bit5M_max5M_buf10M_lcaac_192k_48k_2ch_eng.mp4 | 1280x720 | hevc | Main@12.0 | 50.00 | 10.04s | 502 | OK | 14.95s | 10.98s | OK | 45.7 | 0.00 |  |
| hd | 1920x1080i25_2ch_libx264_high_yuv420p_gop50_bit3584k_max3584k_buf6M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | h264 | High@5.2 | 25.00 | 10.08s | 252 | OK | 13.99s | 10.08s | OK | 25.0 | 0.00 |  |
| hd | 1920x1080i25_2ch_libx264_high_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | h264 | High@5.2 | 25.00 | 10.08s | 252 | OK | 14.13s | 10.15s | OK | 24.8 | 0.00 |  |
| hd | 1920x1080i25_2ch_libx265_main_yuv420p_gop50_bit3584k_max3584k_buf6M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | hevc | Main@12.0 | 25.00 | 10.08s | 252 | OK | 14.72s | 10.58s | OK | 23.8 | 0.00 |  |
| hd | 1920x1080i25_2ch_libx265_main_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | hevc | Main@12.0 | 25.00 | 10.08s | 252 | OK | 15.05s | 10.64s | OK | 23.7 | 0.00 |  |
| hd | 1920x1080p25_2ch_libx264_high_yuv420p_gop50_bit3584k_max3584k_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | h264 | High@5.0 | 25.00 | 10.08s | 252 | OK | 14.26s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 1920x1080p25_2ch_libx264_high_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | h264 | High@5.0 | 25.00 | 10.08s | 252 | OK | 14.30s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 1920x1080p25_2ch_libx265_main_yuv420p_gop50_bit3584k_max3584k_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | hevc | Main@12.0 | 25.00 | 10.08s | 252 | OK | 14.64s | 10.48s | OK | 24.0 | 0.00 |  |
| hd | 1920x1080p25_2ch_libx265_main_yuv420p_gop50_bit5M_max5M_buf10M_lcaac_256k_48k_2ch_ger.mp4 | 1920x1080 | hevc | Main@12.0 | 25.00 | 10.08s | 252 | OK | 15.02s | 10.57s | OK | 23.8 | 0.00 |  |
| hd | 320x180p12_2ch_libx264_baseline_yuv420p_gop25_bit128k_max128k_buf256k_lcaac_56k_48k_2ch_eng.mp4 | 320x180 | h264 | High@1.2 | 12.00 | 10.17s | 122 | OK | 13.86s | 10.05s | OK | 12.1 | 0.00 |  |
| hd | 320x180p12_2ch_libx265_baseline_yuv420p_gop25_bit128k_max128k_buf256k_lcaac_56k_48k_2ch_eng.mp4 | 320x180 | hevc | Main@6.0 | 12.00 | 10.17s | 122 | OK | 13.76s | 10.05s | OK | 12.1 | 0.00 |  |
| hd | 480x270p25_2ch_libx264_baseline_yuv420p_gop50_bit256k_max256k_buf512k_lcaac_64k_48k_2ch_eng.mp4 | 480x270 | h264 | High@2.1 | 25.00 | 10.08s | 252 | OK | 13.72s | 10.02s | OK | 25.1 | 0.00 |  |
| hd | 480x270p25_2ch_libx265_baseline_yuv420p_gop50_bit256k_max256k_buf512k_lcaac_64k_48k_2ch_eng.mp4 | 480x270 | hevc | Main@6.3 | 25.00 | 10.08s | 252 | OK | 13.73s | 10.07s | OK | 25.0 | 0.00 |  |
| hd | 512x288p25_2ch_libx264_main_yuv420p_gop50_bit512k_max512k_buf1024k_lcaac_96k_48k_2ch_eng.mp4 | 512x288 | h264 | High@2.1 | 25.00 | 10.08s | 252 | OK | 13.71s | 10.07s | OK | 25.0 | 0.00 |  |
| hd | 512x288p25_2ch_libx265_main_yuv420p_gop50_bit512k_max512k_buf1024k_lcaac_96k_48k_2ch_eng.mp4 | 512x288 | hevc | Main@6.3 | 25.00 | 10.08s | 252 | OK | 13.90s | 10.16s | OK | 24.8 | 0.00 |  |
| hd | 640x360p25_2ch_libx264_main_yuv420p_gop50_bit1024k_max1024k_buf2M_lcaac_192k_48k_2ch_eng.mp4 | 640x360 | h264 | High@3.0 | 25.00 | 10.08s | 252 | OK | 13.69s | 10.01s | OK | 25.2 | 0.00 |  |
| hd | 640x360p25_2ch_libx265_main_yuv420p_gop50_bit1024k_max1024k_buf2M_lcaac_192k_48k_2ch_eng.mp4 | 640x360 | hevc | Main@6.3 | 25.00 | 10.08s | 252 | OK | 13.83s | 10.11s | OK | 24.9 | 0.00 |  |
| hd | 640x720p50_2ch_libx264_high_yuv420p_gop100_bit1024k_max1024k_buf2M_lcaac_192k_48k_2ch_eng.mp4 | 640x720 | h264 | High@3.1 | 50.00 | 10.04s | 502 | OK | 13.76s | 10.05s | OK | 50.0 | 0.00 |  |
| hd | 640x720p50_2ch_libx265_main_yuv420p_gop100_bit1024k_max1024k_buf2M_lcaac_192k_48k_2ch_eng.mp4 | 640x720 | hevc | Main@9.3 | 50.00 | 10.04s | 502 | OK | 13.82s | 10.00s | OK | 50.2 | 0.00 |  |
| hd | 720x576i25_2ch_libx264_main_yuv420p_gop50_bit1536k_max1536k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 720x576 | h264 | High@3.0 | 25.00 | 10.08s | 252 | OK | 13.85s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 720x576i25_2ch_libx265_main_yuv420p_gop50_bit1536k_max1536k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 720x576 | hevc | Main@9.0 | 25.00 | 10.08s | 252 | OK | 14.01s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 720x576p25_2ch_libx264_main_yuv420p_gop50_bit1536k_max1536k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 720x576 | h264 | High@3.0 | 25.00 | 10.08s | 252 | OK | 13.92s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 720x576p25_2ch_libx265_main_yuv420p_gop50_bit1536k_max1536k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 720x576 | hevc | Main@9.0 | 25.00 | 10.08s | 252 | OK | 13.88s | 10.15s | OK | 24.8 | 0.00 |  |
| hd | 960x540p25_2ch_libx264_main_yuv420p_gop50_bit1800k_max1800k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | h264 | High@3.1 | 25.00 | 10.08s | 252 | OK | 13.81s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 960x540p25_2ch_libx264_main_yuv420p_gop50_bit2500k_max2500k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | h264 | High@3.1 | 25.00 | 10.08s | 252 | OK | 13.87s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 960x540p25_2ch_libx265_main_yuv420p_gop50_bit1800k_max1800k_buf3M_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | hevc | Main@9.0 | 25.00 | 10.08s | 252 | OK | 14.00s | 10.12s | OK | 24.9 | 0.00 |  |
| hd | 960x540p50_2ch_libx264_main_yuv420p_gop100_bit2500k_max2500k_buf6500k_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | h264 | High@3.1 | 50.00 | 10.04s | 502 | OK | 13.72s | 10.02s | OK | 50.1 | 0.00 |  |
| hd | 960x540p50_2ch_libx265_main_yuv420p_gop100_bit2500k_max2500k_buf6500k_lcaac_192k_48k_2ch_eng.mp4 | 960x540 | hevc | Main@9.3 | 50.00 | 10.04s | 502 | OK | 13.81s | 10.05s | OK | 50.0 | 0.00 |  |
| hd | 960x720p50_2ch_libx264_high_yuv420p_gop100_bit2500k_max2500k_buf6500k_lcaac_192k_48k_2ch_eng.mp4 | 960x720 | h264 | High@3.2 | 50.00 | 10.04s | 502 | OK | 13.84s | 10.02s | OK | 50.1 | 0.00 |  |
| hd | 960x720p50_2ch_libx265_main_yuv420p_gop100_bit2500k_max2500k_buf6500k_lcaac_192k_48k_2ch_eng.mp4 | 960x720 | hevc | Main@12.0 | 50.00 | 10.04s | 502 | OK | 13.96s | 10.09s | OK | 49.8 | 0.00 |  |
| hdr | 1080x1080p50_libx264_high_yuv420p_bt709_gop100_bit3650k_lcaac_160k_48k_2ch_en.mp4 | 1080x1080 | h264 | High@4.0 | 50.00 | 9.04s | 452 | OK | 13.44s | 9.53s | OK | 47.4 | 0.00 |  |
| hdr | 1080x1920p50_libx264_high_yuv420p_bt709_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1080x1920 | h264 | High@4.2 | 50.00 | 9.04s | 452 | OK | 20.07s | 15.87s | OK | 28.5 | 0.00 |  |
| hdr | 1280x720p25_libx264_high_yuv420p_bt709_gop50_bit3584k_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.1 | 25.00 | 9.08s | 227 | OK | 13.55s | 9.07s | OK | 25.0 | 0.00 |  |
| hdr | 1280x720p25_libx264_high_yuv420p_bt709_gop50_bit5M_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.1 | 25.00 | 9.08s | 227 | OK | 13.05s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit3584k_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.81s | 9.01s | OK | 50.2 | 0.00 |  |
| hdr | 1280x720p50_libx264_high_yuv420p_bt709_gop100_bit5M_lcaac_160k_48k_2ch_en.mp4 | 1280x720 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.89s | 8.99s | OK | 50.3 | 0.00 |  |
| hdr | 1920x1080p50_libx264_high_yuv420p_bt709_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1920x1080 | h264 | High@4.2 | 50.00 | 9.04s | 452 | OK | 20.42s | 16.44s | OK | 27.5 | 0.00 |  |
| hdr | 1920x1080p50_libx265_main10_yuv420p10le_bt2020-hlg10_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1920x1080 | hevc | Main 10@12.3 | 50.00 | 9.04s | 452 | OK | 59.34s | 54.56s | OK | 8.3 | 0.00 |  |
| hdr | 1920x1080p50_libx265_main10_yuv420p10le_bt2020-pq10_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1920x1080 | hevc | Main 10@12.3 | 50.00 | 9.04s | 452 | OK | 60.77s | 54.42s | OK | 8.3 | 0.00 |  |
| hdr | 1920x1080p50_libx265_main10_yuv420p10le_bt2020-sdr10_gop100_bit6500k_lcaac_160k_48k_2ch_en.mp4 | 1920x1080 | hevc | Main 10@12.3 | 50.00 | 9.04s | 452 | OK | 64.79s | 58.40s | OK | 7.7 | 0.00 |  |
| hdr | 270x270p25_libx264_baseline_yuv420p_bt709_gop50_bit144k_lcaac_96k_48k_2ch_en.mp4 | 270x270 | h264 | Constrained Baseline@1.3 | 25.00 | 9.00s | 225 | OK | 14.00s | 8.93s | OK | 25.2 | 0.00 |  |
| hdr | 270x480p25_libx264_baseline_yuv420p_bt709_gop50_bit256k_lcaac_64k_48k_2ch_en.mp4 | 270x480 | h264 | Constrained Baseline@2.1 | 25.00 | 9.00s | 225 | OK | 12.61s | 8.93s | OK | 25.2 | 0.00 |  |
| hdr | 360x360p25_libx264_main_yuv420p_bt709_gop50_bit576k_lcaac_160k_48k_2ch_en.mp4 | 360x360 | h264 | Main@2.1 | 25.00 | 9.08s | 227 | OK | 12.79s | 9.11s | OK | 24.9 | 0.00 |  |
| hdr | 360x640p25_libx264_main_yuv420p_bt709_gop50_bit1024k_lcaac_160k_48k_2ch_en.mp4 | 360x640 | h264 | Main@3.0 | 25.00 | 9.08s | 227 | OK | 12.89s | 9.11s | OK | 24.9 | 0.00 |  |
| hdr | 3840x2160p50_libx264_high_yuv420p_bt709_gop100_bit10M_lcaac_160k_48k_2ch_en.mp4 | 3840x2160 | h264 | High@5.2 | 50.00 | 9.04s | 452 | Fehler | 22.09s | 0.00s | Fehlerhaft | 0.0 | 0.00 | Exit-Code: 2. No specific error in log. |
| hdr | 3840x2160p50_libx265_main10_yuv420p10le_bt2020-hlg10_gop100_bit7500k_lcaac_160k_48k_2ch_en.mp4 | 3840x2160 | hevc | Main 10@15.3 | 50.00 | 9.04s | 452 | Fehler | 0.00s | 0.00s | Fehlerhaft | 0.0 | 0.00 | Exit-Code: -9. No specific error in log. |
| hdr | 3840x2160p50_libx265_main10_yuv420p10le_bt2020-pq10_gop100_bit7500k_lcaac_160k_48k_2ch_en.mp4 | 3840x2160 | hevc | Main 10@15.3 | 50.00 | 9.04s | 452 | Fehler | 0.00s | 0.00s | Fehlerhaft | 0.0 | 0.00 | Exit-Code: -9. No specific error in log. |
| hdr | 3840x2160p50_libx265_main10_yuv420p10le_bt2020-sdr10_gop100_bit7500k_lcaac_160k_48k_2ch_en.mp4 | 3840x2160 | hevc | Main 10@15.3 | 50.00 | 9.04s | 452 | Fehler | 0.00s | 0.00s | Fehlerhaft | 0.0 | 0.00 | Exit-Code: -9. No specific error in log. |
| hdr | 480x270p25_libx264_baseline_yuv420p_bt709_gop50_bit256k_lcaac_128k_48k_2ch_en.mp4 | 480x270 | h264 | Constrained Baseline@2.1 | 25.00 | 9.00s | 225 | OK | 15.13s | 8.94s | OK | 25.2 | 0.00 |  |
| hdr | 512x288p25_libx264_main_yuv420p_bt709_gop50_bit512k_lcaac_160k_48k_2ch_en.mp4 | 512x288 | h264 | Main@2.1 | 25.00 | 9.08s | 227 | OK | 12.89s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 540x540p25_libx264_main_yuv420p_bt709_gop50_bit1150k_lcaac_160k_48k_2ch_en.mp4 | 540x540 | h264 | Main@3.0 | 25.00 | 9.08s | 227 | OK | 12.88s | 9.05s | OK | 25.1 | 0.00 |  |
| hdr | 540x960p25_libx264_main_yuv420p_bt709_gop50_bit1800k_lcaac_160k_48k_2ch_en.mp4 | 540x960 | h264 | Main@3.1 | 25.00 | 9.08s | 227 | OK | 12.90s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 640x360p25_libx264_main_yuv420p_bt709_gop50_bit1024k_lcaac_160k_48k_2ch_en.mp4 | 640x360 | h264 | Main@3.0 | 25.00 | 9.08s | 227 | OK | 12.89s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 720x1280p25_libx264_high_yuv420p_bt709_gop50_bit3584k_lcaac_160k_48k_2ch_en.mp4 | 720x1280 | h264 | High@3.1 | 25.00 | 9.08s | 227 | OK | 12.94s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 720x1280p50_libx264_high_yuv420p_bt709_gop100_bit5M_lcaac_160k_48k_2ch_en.mp4 | 720x1280 | h264 | High@3.2 | 50.00 | 9.04s | 452 | OK | 12.94s | 9.01s | OK | 50.2 | 0.00 |  |
| hdr | 720x720p25_libx264_high_yuv420p_bt709_gop50_bit2250k_lcaac_160k_48k_2ch_en.mp4 | 720x720 | h264 | High@3.1 | 25.00 | 9.08s | 227 | OK | 12.92s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 960x540p25_libx264_main_yuv420p_bt709_gop50_bit2500k_lcaac_160k_48k_2ch_en.mp4 | 960x540 | h264 | Main@3.1 | 25.00 | 9.08s | 227 | OK | 12.98s | 9.08s | OK | 25.0 | 0.00 |  |
| hdr | 960x540p50_libx264_main_yuv420p_bt709_gop100_bit2500k_lcaac_160k_48k_2ch_en.mp4 | 960x540 | h264 | Main@3.1 | 50.00 | 9.04s | 452 | OK | 12.72s | 8.99s | OK | 50.3 | 0.00 |  |

### Attribution
*   **Author of modifications:** Martin Schmalohr
*   **AI-assisted development:** Some of the scripts and modifications in this fork were developed with the assistance of Google's Gemini.
