2025-09-30 10:00:00:
* State: The user wants to fix an issue with the vertical scrolling effect for portrait images. The images are stretched horizontally.
* Problem: Portrait images are stretched horizontally during vertical scrolling.
* Solution: I have corrected the aspect ratio calculation in `__apply_kenburns_transform` in `viewer_display.py` to prevent the horizontal stretching of portrait images.

2025-09-30 10:05:00:
* State: The fix for the Ken Burns effect has been applied.
* Problem: The aspect ratio correction was faulty.
* Solution: I have replaced the incorrect aspect ratio logic in `viewer_display.py` with a version that correctly compensates for texture stretching, ensuring images are displayed with the proper proportions.

2025-10-01 10:00:00:
* State: The user reported that the Ken Burns vertical scrolling for portrait images starts and ends at the wrong positions.
* Problem: The scrolling animation for portrait images is confined to a small area in the center, leaving large borders, instead of scrolling from edge to edge with a small border offset.
* Solution: I have corrected the calculation of the start and end points for the vertical panning in `__calculate_kenburns_transform` in `viewer_display.py`. The logic now uses the full overshoot range and applies a random border based on `kenburns_portrait_border_pct`, and also corrects the inverted `up`/`down` direction logic.

2025-10-01 10:30:00:
* State: The user reported that the previous fix for vertical scrolling was not effective.
* Problem: The scrolling still starts "outside the image borders", indicating the calculated offset is too large.
* Solution: I identified the root cause in `__apply_kenburns_transform`. The conversion from pixel offset to the shader's uniform offset was missing a division by the texture scale factor (`scale_y`). I have corrected the formula to `offset_y_unif = (offset_y / self.__display.height) / scale_y`, which should correctly scale the pan/scroll effect.

2025-10-02 10:00:00:
* State: The user wants to refine the Ken Burns effect for portrait and landscape images.
* Problem: For portrait images, horizontal panning can reveal black bars at the edges. For landscape images, the zoom factor and panning are not random, appearing static and centered.
* Solution: I have refactored `__calculate_kenburns_transform` in `viewer_display.py`. For portrait images, I added a slight zoom to prevent black bars. For landscape images, I implemented randomization for both the zoom factor and the panning amount and direction, based on the user's YAML configuration.
2025-10-03 09:00:00:
* State: The user observed that the Ken Burns pan/wobble effect for landscape images was not noticeable.
* Problem: The calculation for the pan/wobble range was based on a percentage of the image's "overshoot" (the part of the image outside the screen). This overshoot can be very small if the image's aspect ratio is close to the screen's, making the effect invisible.
* Solution: The code in `viewer_display.py` was modified to calculate the pan/wobble range as a percentage of the display's width and height, similar to how it's done for portrait images. This makes the effect's magnitude dependent on the screen size, which is more intuitive and consistent. The calculated pan is still clamped to the maximum possible overshoot to avoid showing black bars.
2025-10-03 10:00:00:
* State: The user reported seeing black borders at the start/end of the Ken Burns zoom effect for landscape images after the previous change.
* Problem: The allowed panning range was calculated based on the zoom level at only one point of the animation (the most zoomed point). This caused the pan to exceed the image boundaries when the image was less zoomed, revealing the background.
* Solution: The logic in `__calculate_kenburns_transform` in `viewer_display.py` was corrected. The pannable area (overshoot) and the resulting allowed wobble/pan range are now calculated independently for both the start and end zoom levels of the animation. This ensures the pan is always constrained correctly, eliminating the black borders.
2025-10-03 11:00:00:
* State: The user reported that the zoom for portrait images is too high when using a large `kenburns_wobble_pct` for landscape images.
* Problem: The same `kenburns_wobble_pct` was used for both landscape pan and portrait zoom/pan, leading to undesirable coupling of the effects.
* Solution: Split the `kenburns_wobble_pct` parameter into `kenburns_landscape_wobble_pct` and `kenburns_portrait_wobble_pct`. The logic in `viewer_display.py` was updated to use these new orientation-specific parameters. The `configuration_example.yaml` was also updated to reflect this change, giving the user independent control over the effects.

2025-10-03 15:30:00:
* State: The user reported a `SyntaxError` in `src/picframe/viewer_display.py`.
* Problem: A typo (`e` at the end of a line) and duplicated methods at the end of the file caused a `SyntaxError`.
* Solution: I have corrected the typo and removed the duplicated methods in `src/picframe/viewer_display.py`.

2025-10-04 13:00:00:
* State: The user reported an `AttributeError` in `src/picframe/viewer_display.py`.
* Problem: The attributes `__kb_landscape_wobble_pct` and `__kb_portrait_wobble_pct` were used but not initialized in the `__init__` method. The old `__kb_wobble_pct` was still being used for portrait images.
* Solution: I have corrected the `__init__` method to initialize the new landscape and portrait wobble attributes. I also updated the `__calculate_kenburns_transform` method to use `__kb_portrait_wobble_pct` for portrait images.

2025-10-04 14:00:00:
* State: The user observed that the Ken Burns effect for landscape images has inconsistent strength.
* Problem: The panning strength was dependent on the image's aspect ratio, making the effect weaker for images with aspect ratios close to the display's.
* Solution: I have modified `viewer_display.py` to enforce a minimum zoom level to guarantee enough overshoot for the desired panning, making the effect consistent.

2025-10-04 14:20:00:
* State: The user reported that the `pir_manager.py` service was failing after they moved the scripts directory.
* Problem: The path to the script was hardcoded in `install.sh`.
* Solution: I have corrected the `SCRIPT_DIR` variable in `install.sh` to point to the new location.

2025-10-04 14:25:00:
* State: The user reported a `FileNotFoundError` for `configuration.yaml` after moving files.
* Problem: The default path to the configuration file was hardcoded in `model.py`.
* Solution: I explained to the user how to pass the correct config file path as an argument in `watcher.sh`.

2025-10-04 14:30:00:
* State: The user reported errors in `sync_photos.sh` due to Windows line endings.
* Problem: The script had `CRLF` line endings, which are not compatible with Linux shells.
* Solution: I explained the cause of the issue and provided the user with the `dos2unix` command to fix the file on their system.

2025-10-05 10:00:00:
* State: The user requested a new shell script to check and correct image dates.
* Problem: The user needs a script to verify and fix image dates based on directory names and EXIF data.
* Solution: I have created a new shell script `check_pic_dates.sh` in the `scripts` directory. The script iterates through year-named directories, compares file dates with directory and EXIF years, and provides options to fix dates and move files accordingly. All actions are logged.

2025-10-05 10:10:00:
* State: The user reported that the `check_pic_dates.sh` script is missing the `exiftool` dependency.
* Problem: The `exiftool` command is not found when running the script.
* Solution: I have updated the `install.sh` script to include the installation of `libimage-exiftool-perl`, which provides the `exiftool` command.

2025-10-05 10:20:00:
* State: The user reported that the `clock_hgt_offset_pct` setting for the clock is not working as expected.
* Problem: A small percentage value for `clock_hgt_offset_pct` results in a much larger visual offset.
* Solution: I have corrected the formula for the clock's vertical position in `viewer_display.py` to accurately reflect the percentage-based offset.

2025-10-05 14:20:00:
* State: The user reported an error with the `check_pic_dates.sh` script.
* Problem: The `touch` command fails with an invalid date format error because a hyphen is used between the month and day.
* Solution: I have corrected the `check_pic_dates.sh` script to use the `+%m%d` format for the date, which is compatible with the `touch -t` command.

2025-10-05 14:30:00:
* State: The user requested a new 'A' (All) option in the `check_pic_dates.sh` script.
* Problem: The user wants to process all directories without being prompted for each one.
* Solution: I have added an 'A' option to the script. When selected, it sets a flag to process all subsequent directories without further confirmation.

2025-10-05 14:40:00:
* State: The user reported a syntax error in the `check_pic_dates.sh` script.
* Problem: The script has a syntax error `;&&` in a case statement.
* Solution: I have corrected the syntax error by changing `;&&` to `;&`.
