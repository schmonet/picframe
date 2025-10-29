import subprocess
import logging
import time
import os

# --- Configuration ---
IMAGE_PATH = "/home/schmali/picframe/test/images/1920x1080.jpg"
VIDEO_PATH = "/home/schmali/picframe/test/videos/hd/1280x720p25_6bar_2ch_libx264_high_yuv420p_gop50_bit2500k_max2500k_buf7M_lcaac_192k_48k_2ch_eng.mp4"
IMAGE_DURATION = "10"  # As a string for subprocess args
LOOP_COUNT = 3
PYTHON_EXECUTABLE = "python3" # Or specify full path if needed
SHOW_IMAGE_SCRIPT = os.path.join(os.path.dirname(__file__), "test_show_image.py")

# Framebuffer settings from udevadm output
FB_WIDTH = 1920
FB_HEIGHT = 1080
FB_BPP = 16 # bits_per_pixel
FB_BYTES = int(FB_WIDTH * FB_HEIGHT * (FB_BPP / 8))

# --- Logging Setup ---
LOG_FORMAT = '%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger(__name__)

def set_cursor(visible: bool):
    logger.info(f"--- Setting cursor visibility: {visible} ---")
    term_arg = "on" if visible else "off"
    try:
        subprocess.run(["setterm", "-cursor", term_arg], check=True, capture_output=True)
    except Exception as e:
        logger.warning(f"Could not set cursor state: {e}")

def show_black_screen():
    logger.info("--- Showing Black Screen via dd ---")
    command = ["dd", "if=/dev/zero", f"of=/dev/fb0", f"bs={FB_BYTES}", "count=1"]
    logger.info(f"Executing command: {' '.join(command)}")
    try:
        # This requires write permission to /dev/fb0, which the 'video' group should have.
        subprocess.run(command, check=True, capture_output=True)
        logger.info("dd command completed successfully.")
    except Exception as e:
        logger.warning(f"Could not blank screen with dd: {e}")

def clear_console():
    logger.info("--- Clearing console ---")
    try:
        subprocess.run(["clear"], check=True, capture_output=True)
    except Exception as e:
        logger.warning(f"Could not clear console: {e}")

def display_image_subprocess(image_path, duration):
    logger.info(f"--- Starting Image Display via Subprocess ---")
    command = [PYTHON_EXECUTABLE, SHOW_IMAGE_SCRIPT, image_path, duration]
    logger.info(f"Executing command: {' '.join(command)}")
    try:
        result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=int(duration) + 5)
        logger.info("Image display script finished successfully.")
        logger.debug("Image script stdout:\n" + result.stdout)
        logger.debug("Image script stderr:\n" + result.stderr)
    except Exception as e:
        logger.error(f"An error occurred running image display script: {e}")
    logger.info(f"--- Finished Image Display via Subprocess ---")

def play_video_subprocess(video_path):
    logger.info("--- Starting Video Playback via Subprocess ---")
    command = ["cvlc", "--fullscreen", "--no-video-title-show", video_path, "vlc://quit"]
    logger.info(f"Executing command: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, timeout=120)
        logger.info("Video playback finished successfully.")
    except Exception as e:
        logger.error(f"An error occurred during video playback: {e}")
    logger.info("--- Finished Video Playback via Subprocess ---")

def main():
    logger.info("Starting orchestrator script.")
    # Hide cursor for the entire duration of the script
    set_cursor(False)
    for i in range(1, LOOP_COUNT + 1):
        logger.info(f"\n=============== LOOP {i} of {LOOP_COUNT} ===============")
        display_image_subprocess(IMAGE_PATH, IMAGE_DURATION)
        
        # Blank the screen to hide the console
        show_black_screen()
        time.sleep(0.2) # Give it a moment

        play_video_subprocess(VIDEO_PATH)

        # Clear console in case VLC messed it up
        clear_console()
        time.sleep(0.2) # Small pause before next loop
    
    logger.info("\n=============== SCRIPT FINISHED ===============")
    # Hide cursor one last time before exiting to override shell restoration
    set_cursor(False)

if __name__ == "__main__":
    main()