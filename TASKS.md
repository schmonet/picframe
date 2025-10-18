Date: 2025-10-13 13:00:00

**Current State:**
The user has confirmed that `ffmpeg` is installed, but the `ffprobe` command is not found when running as a service.

**Problem:**
The `PATH` environment variable for the `picframe` service does not include the directory where `ffprobe` is located. This causes the `FileNotFoundError`.

**Solution:**
I have implemented a more robust solution by adding a new configuration option `ffprobe_path` in the `model` section of the `configuration.yaml` file.

1.  **`src/picframe/model.py`**: Added `ffprobe_path: None` to the default configuration and passed it to the `ImageCache`.
2.  **`src/picframe/image_cache.py`**: Modified `ImageCache` to accept `ffprobe_path` and pass it to `get_video_info`.
3.  **`src/picframe/video_streamer.py`**: Modified `get_video_info` to use the `ffprobe_path` if provided, otherwise it falls back to the default `ffprobe` command.

This allows the user to explicitly set the path to `ffprobe` in their configuration file, bypassing any `PATH` issues with the systemd service.

I have informed the user about this new configuration option and advised them to find the path of `ffprobe` using `which ffprobe` and add it to their `configuration.yaml`.

Date: 2025-10-14 20:30:00

**Current State:**
The user wants to start the picframe slideshow when presence is detected during the night, even before the scheduled start time.

**Problem:**
The `pir_manager.py` script would only turn on the screen but not start the `picframe` service if motion was detected during the night-off hours. The slideshow would only start at the scheduled time (e.g., 7 AM).

**Solution:**
I have modified `scripts/pir_manager.py` to implement the desired behavior.
1.  **Night Override:** Introduced a `night_override` flag. When motion is detected during the night (`STATE_OFF`), this flag is set to `True`.
2.  **Immediate Start:** If motion is detected during the night, the script now immediately starts the `picframe` service and turns on the display.
3.  **Persistent State:** The `night_override` flag prevents the script from turning off the service again during the same night cycle, even if no more motion is detected for a while.
4.  **Reset:** The flag is automatically reset when the scheduled day-time begins.
5.  **Bugfix:** Corrected the config file path handling to properly expand the `~` character.

Date: 2025-10-18 18:00:00

**Current State:**
The user requested a script to create test images from PNG files, overlaying metadata and adding random EXIF data.

**Problem:**
The initial versions of the `create_test_images.sh` script had several issues, including syntax errors in arithmetic expressions, locale-dependent number formatting problems (`printf`), and suboptimal text rendering for different image orientations.

**Solution:**
I created and iteratively refined the `scripts/create_test_images.sh` script.
1.  **Conversion & Metadata:** The script converts PNG files to JPG, reads image dimensions and color space using `mediainfo`, and burns this information onto the new JPG image using `imagemagick`.
2.  **Random EXIF Data:** It uses `exiftool` to add randomized, plausible EXIF data, including GPS coordinates selected from a predefined list of capital cities.
3.  **Bug Fixing:**
    - Corrected shell arithmetic syntax (`$((...))` for ImageMagick calculations).
    - Forced a `C` locale for `printf` to ensure consistent decimal point formatting (`LC_NUMERIC=C`).
4.  **Enhancements:**
    - Differentiated between landscape and portrait images.
    - For portrait images, the text position was lowered, the font size was increased by 15%, and the font weight and outline were adjusted for better readability.

Date: 2025-10-18 18:30:00

**Current State:**
The user asked to commit a series of changes to the git repository.

**Problem:**
There were several modified and untracked files that needed to be committed. This included documentation updates, script changes, and new test media.

**Solution:**
I performed the following actions:
1.  **`git status`**: Reviewed the state of the repository to identify all changes.
2.  **`git add -A`**: Staged all new and modified files, including documentation, scripts, and the entire `test/images` and `test/videos` directories.
3.  **`git commit`**: Committed the staged changes with the message "docs: update documentation and scripts".
4.  **`git push`**: Pushed the new commit to the `origin/main` branch on GitHub.
