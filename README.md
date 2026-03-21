## PictureFrame powered by pi3d

![picframe logo](https://github.com/helgeerbe/picframe/wiki/images/Picframe_Logo.png)

## What Is PictureFrame?

This is a highly customizable photo and video viewer for a Raspberry Pi-powered digital picture frame. For remote control, it provides an automatic integration into [Home Assistant](https://www.home-assistant.io/) via MQTT discovery.

- https://github.com/helgeerbe/picframe
- Paddy Gaunt, Jeff Godfrey, Helge Erbe
- Licence: MIT
- Tested on Raspberry 3B+/4 and Zero 2, Ubuntu 20.10 and Python 3.7+

## Fork Information

This repository is a fork of the original [picframe by helgeerbe](https://github.com/helgeerbe/picframe). It includes several modifications and new scripts to enhance functionality, performance, and automation.

*   **Author of modifications:** Martin Schmalohr
*   **AI-assisted development:** Some of the scripts and modifications in this fork were developed with the assistance of Google's Gemini.

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

### Required Settings for Headless Operation with Pi3D

To run PicFrame successfully on a headless Raspberry Pi (i.e., without a desktop environment like X11 or Wayland), the following settings are crucial. They ensure that the Pi3D graphics library uses the correct video driver (KMS/DRM) instead of searching for a non-existent graphical display.

*   **In `/boot/config.txt`:**
    *   The KMS (Kernel Mode Setting) video driver must be activated. Ensure this line is present and not commented out:
        ```
        dtoverlay=vc4-kms-v3d
        ```

*   **In `/boot/cmdline.txt`:**
    *   It is highly recommended to explicitly set the video mode for your connected display. Add the following to the single line in this file (adjust resolution and refresh rate as needed):
        ```
        video=HDMI-A-1:1920x1080@50
        ```

*   **In your `configuration.yaml`:**
    *   You must configure PicFrame to use the correct Pi3D backend.
        *   `use_glx:` must be set to `false`. This prevents Pi3D from trying to use the GLX extension, which requires an X-Server.
        *   `use_sdl2:` must be set to `true`. This enables the SDL2 backend, which can render directly to the hardware framebuffer.
        ```yaml
        viewer:
          use_glx: false
          use_sdl2: true
        ```

**Important:** If these settings are not configured correctly, Pi3D cannot find a valid display and will fail to start. This typically results in an OpenGL-related error message in the logs, such as the one we encountered: `AssertionError: Couldnt open DISPLAY None`.


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

For a detailed visual representation of the application flow, including media type decision, image pre-processing, and Ken Burns logic, see the **Workflow Diagram**.

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

To handle videos without compromising the stability of the `pi3d` graphics engine, two distinct methods are supported.

##### Method 1: Full Video Playback with `mpv` (Default)

Stable playback of entire video files is achieved through a controlled restart of the application:

*   **Detection:** `picframe` determines that the next file in the playlist is a video.
*   **Set Bookmark:** It saves the path of the *next* image file (the one that should come after the video) to the state file `shown_albums.log`.
*   **Play Video:** The external player `mpv` is started and plays the video in full-screen mode.
*   **Exit with Signal:** After the video, `picframe` exits itself with the special **Exit Code 10**.
*   **Restart by Watcher:** The `watcher.sh` script, which monitors `picframe`, detects exit code 10 and immediately restarts the application. All other exit codes would terminate the service.
*   **Resumption:** On restart, `picframe` reads the bookmark from `shown_albums.log`, finds the corresponding file in the playlist, and resumes the slideshow exactly at that point.

##### Method 2: Video Slideshow with `ffmpeg` (Alternative)

This method treats videos not as movies, but as a sequence of still images that are seamlessly blended into the slideshow. This completely avoids application restarts.

*   **External Preprocessing:** A separate, external script (`video_preprocessor.py`) runs in the background.
*   **Find Videos:** This script scans the image directories for video files.
*   **Extract Frames:** For each new video, it uses `ffmpeg` to extract individual frames at regular intervals (e.g., every 10 seconds).
*   **Save as Images:** The extracted frames are saved as standard `.jpg` files in a dedicated subfolder (e.g., `MyVideo.mp4_frames/`).
*   **Automatic Discovery:** The main `picframe` application is "video-blind". It automatically discovers the new folder of images via its existing `ImageCache` mechanism.
*   **Seamless Integration:** The extracted frames are treated like normal photos and are integrated into the regular slideshow with cross-fading effects, but excluding Ken Burns.

### Video Playback Configuration

PicFrame uses `ffmpeg` to extract frames from videos for seamless integration into the 3D slideshow. You can tune the performance and quality with the following options in `configuration.yaml` under the `model` section:

*   **`video_slideshow_quality`**: (int, default: 6) Controls the quality of the extracted JPEG frames. The range is 2-31, where lower numbers mean higher quality (and larger file sizes).
*   **`video_slideshow_temp_dir`**: (string, optional) Path to a directory for temporary frame storage. If not set, the system temporary directory is used. Using a RAM disk or fast storage is recommended to reduce SD card wear.
*   **`video_slideshow_step_time`**: (float, default: 10.0) Time in seconds between extracted keyframes.
*   **`video_slideshow_time_delay`**: (float, default: 4.0) How long each extracted frame is displayed.

**Hardware Acceleration:**
The system automatically attempts to use hardware acceleration (`h264_v4l2m2m`) on Raspberry Pi for H.264 content to minimize CPU usage.


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

### New Task: Video Integration as External Preprocessing Process

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

### Recommended Setup for Pi Zero 2

To operate the video slideshow stably, it is strongly recommended to use a USB stick for temporary files:

1.  Format USB stick with `ext4` (faster/less CPU load than FAT32).
2.  Mount under e.g., `/mnt/usb`.
3.  Configuration/Call with `--temp-dir /mnt/usb`.

### Attribution
*   **Author of modifications:** Martin Schmalohr
*   **AI-assisted development:** Some of the scripts and modifications in this fork were developed with the assistance of Google's Gemini.

### Parameter-Beschreibung

* **fit**

  * `true`: Bild wird so skaliert, dass es vollständig sichtbar ist. Es entstehen schwarze Ränder ("Letterboxing" oder "Pillarboxing").
  * `false`: Bild wird so skaliert, dass es den Bildschirm füllt. Überstehende Teile werden abgeschnitten (Crop).
  * **Hinweis:** Wird ignoriert, wenn `kenburns: true`.

* **crop_to_aspect_ratio**
  Erzwingt ein bestimmtes Seitenverhältnis (z.B. `"4:3"` oder `"16:9"`) durch Zuschneiden des Bildes vor der Anzeige.

  * `null` (Standard): Kein erzwungener Zuschnitt.

* **kenburns**

  * `true`: Aktiviert den Ken-Burns-Effekt (sanftes Zoomen und Schwenken). Setzt implizit `fit: false`.
  * `false`: Statische Anzeige des Bildes.

* **kenburns_zoom_direction** (nur Querformat)

  * `"random"`: Zufällige Wahl zwischen Zoom-In und Zoom-Out.
  * `"in"`: Bild vergrößert sich (Zoom hinein).
  * `"out"`: Bild verkleinert sich (Zoom heraus).

* **kenburns_zoom_pct** (nur Querformat)
  Prozentualer Zoom-Faktor (z.B. `35.0` für 35%). Bestimmt, wie stark hinein- oder herausgezoomt wird.

* **kenburns_landscape_wobble_pct** (nur Querformat)
  Maximale seitliche/vertikale Verschiebung (Wobble) in Prozent des möglichen Pan-Bereichs, wenn `kenburns_random_pan: true`.

* **kenburns_portrait_wobble_pct** (nur Hochformat)
  Maximale horizontale Verschiebung in Prozent, um dem Scrollen eine leichte seitliche Bewegung zu geben.

* **kenburns_random_pan**

  * `true`: Fügt dem Zoom (Querformat) oder Scrollen (Hochformat) eine zufällige seitliche Verschiebung hinzu.
  * `false`: Zoom erfolgt strikt zentriert; Scrollen erfolgt strikt vertikal.

* **kenburns_scroll_direction** (nur Hochformat)

  * `"random"`: Zufällige Wahl zwischen Scrollen nach oben oder unten.
  * `"up"`: Bild bewegt sich nach oben (Blick wandert von unten nach oben).
  * `"down"`: Bild bewegt sich nach unten (Blick wandert von oben nach unten).

* **kenburns_portrait_border_pct** (nur Hochformat)
  Prozentualer Bereich oben und unten, der beim Scrollen ausgespart wird (Start/Ende nicht direkt am Bildrand), um „tote“ Bereiche zu vermeiden oder den Fokus zentraler zu halten.

## Ken Burns Logic & Configuration

### 1. Smart Downscaling (Performance Optimization)
To ensure smooth performance on hardware with limited RAM (like Raspberry Pi Zero 2) while maintaining high image quality, images are resized **before** being uploaded to the GPU.

*   **Logic:** The system calculates the exact target resolution required to display the image at its maximum zoom level without quality loss (1:1 pixel mapping).
*   **Calculation:**
    *   **Viewport Awareness:** Uses the configured `viewport_aspect_ratio` (e.g., "3:2") rather than just the screen resolution.
    *   **Fit-Width (Portrait on Landscape):** If the image is narrower than the viewport, the target width is calculated as `Viewport Width * (1.0 + Wobble %)`. The height is scaled accordingly.
    *   **Fit-Height (Landscape on Landscape):** If the image is wider than the viewport but not a panorama, the target height is calculated as `Viewport Height * (1.0 + Zoom %)`. The width is scaled accordingly.
    *   **Fit-Height (Panorama):** If the image is wider than the screen aspect ratio, the target height is calculated as `Viewport Height * (1.0 + Panorama Zoom %)`. The width is scaled accordingly to allow for horizontal scrolling.
*   **Result:** Massive reduction in RAM usage and IO-Wait for high-resolution images (e.g., 20MP) without blurring the displayed content.

### 2. Landscape Mode Logic
Applied when the image aspect ratio is **wider** than the viewport but **narrower** than the screen aspect ratio.

*   **Movement:** Focuses on zooming in or out.
*   **Zoom In:**
    *   **Start:** Scale 1.0 (Perfect fit, centered, no cropping).
    *   **End:** Scale `1.0 + Random(0, zoom_pct)`.
    *   **Wobble:** If `random_pan` is enabled, the end position shifts slightly off-center (max `landscape_wobble_pct`) to create a dynamic effect.
*   **Zoom Out:**
    *   **Start:** Scale `1.0 + Random(0, zoom_pct)`.
    *   **Wobble:** If `random_pan` is enabled, the start position is slightly off-center (max `landscape_wobble_pct`).
    *   **End:** Scale 1.0 (Perfect fit, centered, no cropping).
*   **Goal:** Ensures that every landscape transition starts or ends with the full image visible, avoiding permanent cropping while adding cinematic movement.

### 3. Portrait Mode Logic
Applied when the image aspect ratio is **narrower** than the viewport aspect ratio.

*   **Movement:** Focuses on vertical scrolling (Panorama effect).
*   **Scaling:** The image width is fitted to the viewport width (`Fit Width`). The excess height is used for scrolling.
*   **Scrolling:**
    *   Moves from Top-to-Bottom or Bottom-to-Top based on `portrait_scroll_direction`.
    *   **Virtual Cropping:** If `portrait_crop_to_aspect_ratio` is set (e.g., "3:4"), the scrollable area is limited. The system calculates how tall the image *would* be at that aspect ratio and limits the scroll range (`max_y`) to that "virtual" height, ignoring the rest of a very tall panorama.
*   **Wobble:**
    *   If `random_pan` is enabled, a slight zoom (`portrait_wobble_pct`) is applied.
    *   This creates "slack" on the horizontal axis, allowing for a random horizontal drift (Pan X) during the vertical scroll, making the movement feel less robotic.

### 4. Panorama Mode Logic
Applied when the image aspect ratio is **wider** than the screen aspect ratio.

*   **Movement:** Focuses on horizontal scrolling.
*   **Scaling:** The image height is fitted to the viewport height (`Fit Height`). The excess width is used for scrolling.
*   **Scrolling:**
    *   Moves from Left-to-Right or Right-to-Left based on `kenburns_panorama_scroll_direction`.
    *   **Virtual Cropping:** If `panorama_crop_to_aspect_ratio` is set (e.g., "3:1"), the scrollable area is limited, similar to the portrait logic.
*   **Zoom:**
    *   Can optionally zoom in or out during the scroll based on `kenburns_panorama_zoom_pct`.
*   **Wobble:**
    *   If `random_pan` is enabled, a slight vertical drift (Pan Y) is added during the horizontal scroll.

### 5. Configuration Parameters (`configuration.yaml`)

#### Aspect Ratios
*   **`screen_aspect_ratio`** (e.g., `"16:9"`)
    *   The physical aspect ratio of the monitor. Used for sanity checks.
*   **`viewport_aspect_ratio`** (e.g., `"3:2"`)
    *   **Crucial:** Defines the visible area within the screen (e.g., if a physical mat covers parts of the screen). All Ken Burns calculations (centering, scaling limits) are relative to this ratio, not the full screen.
*   **`portrait_crop_to_aspect_ratio`** (e.g., `"3:4"`)
    *   Limits the vertical scroll range for tall portrait images.
*   **`landscape_crop_to_aspect_ratio`**
    *   Usually `null` for Ken Burns to allow full usage of the image width.
*   **`panorama_crop_to_aspect_ratio`** (e.g., `"3:1"`)
    *   Limits the horizontal scroll range for extremely wide panorama images.

#### Ken Burns Settings
*   **`kenburns`** (`true`/`false`)
    *   Master switch. If true, overrides `fit` settings.
*   **`kenburns_random_pan`** (`true`/`false`)
    *   Enables the "Wobble" effect (off-center drift) for Landscape, Portrait, and Panorama.
*   **`kenburns_landscape_zoom_pct`** (float, e.g., `35.0`)
    *   The maximum percentage an image is zoomed in (or starts zoomed out). `35.0` means max scale 1.35.
*   **`kenburns_landscape_wobble_pct`** (float, e.g., `10.0`)
    *   How much the image can drift off-center at the zoomed state (percentage of the available slack).
*   **`kenburns_landscape_zoom_direction`** (`"random"`, `"in"`, `"out"`)
    *   Direction of the animation.
*   **`kenburns_portrait_wobble_pct`** (float, e.g., `8.0`)
    *   Adds a slight zoom to portrait images to allow for horizontal drifting.
*   **`kenburns_portrait_scroll_direction`** (`"random"`, `"up"`, `"down"`)
    *   Direction of the vertical scroll.
*   **`kenburns_panorama_zoom_pct`** (float, e.g., `10.0`)
    *   Zoom percentage applied during panorama scrolling.
*   **`kenburns_panorama_zoom_direction`** (`"random"`, `"in"`, `"out"`)
    *   Zoom direction for panoramas.
*   **`kenburns_panorama_scroll_direction`** (`"random"`, `"left"`, `"right"`)
    *   Direction of the horizontal scroll for panoramas.

#### Transition Settings
*   **`time_delay`** (float)
    *   Duration of the Ken Burns effect (how long the image is shown).
*   **`fade_time`** (float)
    *   Duration of the cross-fade transition between images.

### Logic of `pir_manager.py`

The control is based on **inactivity** (time since last motion) and **time of day** (Day/Night).

#### The 4 States

1.  **ON (Normal Operation)**
    *   **Trigger:** Motion detected or script start.
    *   **Actions:**
        *   Display: **ON** (via `cec-client`).
        *   Service: **Started** (`picframe.service`).
        *   Slideshow: **Play** (Unpause via HTTP).
        *   WiFi: Explicitly unblocked (`rfkill unblock wifi`).

2.  **HOLD (Pause)**
    *   **Trigger:** No motion for **60 minutes** (`3600` seconds).
    *   **Actions:**
        *   Slideshow: **Pause** (via HTTP). The current image remains static.
        *   Display: Remains **ON**.

3.  **BLACK (Screen Off)**
    *   **Trigger:** No motion for **2 hours** (`7200` seconds).
    *   **Actions:**
        *   Display: **OFF** (Standby via `cec-client`).
        *   Slideshow: Remains paused.

4.  **OFF (Night Mode)**
    *   **Trigger:** Time between **23:00 and 06:00** (and no motion).
    *   **Actions:**
        *   Display: **OFF**.
        *   Service: **Stopped** (`systemctl stop picframe.service`). This saves the most power as CPU load drops.

#### Specials regarding Motion (PIR)

*   **Immediate Wake-up:** Regardless of the state (HOLD, BLACK, OFF), motion immediately switches everything on (State **ON**).
*   **Night Override:** If motion is detected at night, the system wakes up and **stays on for the rest of the night** (ignores the night schedule until 06:00 morning), so it doesn't turn off immediately if you stay still for a moment.

### Status Icons & Visual Feedback
The viewer now displays icons in the bottom right corner to indicate specific system states:
*   **`play.png`**: Normal slideshow operation.
*   **`pause.png`**: Slideshow paused (via menu or PIR sensor).
*   **`sync.png`**: Playlist is updating or scanning for new files.
*   **`download.png`**: Sync script is currently downloading new files from the server.
*   **`offline.png`**: SMB Server is unreachable.
*   **`nowlan.png`**: WiFi interface is blocked (e.g., during Night Mode).
*   **`skipf.png`**: Video slideshow (ffmpeg) is playing.
*   **`eject.png`**: No files found in cache.

### Synchronization Script (`sync_photos.sh`)
*   **Unified Cache**: Uses a single directory structure for both photos and videos.
*   **Smart Quotas**: Manages separate storage quotas for photos and videos.
*   **Priority Logic**: Prioritizes photo synchronization; videos are only synced if the photo quota allows.
*   **Auto-Start**: Automatically triggered by the application if the local cache is found to be empty on startup.

### Console Stealth Mode (TTY)
To provide a clean aesthetic, the HDMI console background is set to black after boot, hiding the login prompt and boot messages.
*   **Enable**: Run `sudo ./scripts/set_tty_color.sh` to install the systemd service.
*   **Unhide (via SSH)**: To make the console visible again for maintenance (e.g., to log in locally), run the following command via SSH:
    ```bash
    sudo sh -c 'setterm -default > /dev/tty1'
    ```
