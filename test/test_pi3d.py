# /home/schmali/test_pi3d.py
import pi3d
import logging
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    logger.info("Attempting to create pi3d.Display...")
    # Create a display with minimal settings, similar to picframe
    display = pi3d.Display.create(
        background=(0.2, 0.2, 0.3, 1.0),
        use_sdl2=True # This is a key setting from your config
    )
    logger.info("pi3d.Display created successfully!")
    logger.info("Display size: %d x %d", display.width, display.height)

    # Create a simple shape to draw to confirm it works
    shader = pi3d.Shader("uv_flat")
    sprite = pi3d.Sprite(w=200, h=200, z=5)
    sprite.set_shader(shader)
    sprite.set_material((1.0, 0.0, 0.0)) # Make it red

    logger.info("Displaying a red square for 10 seconds...")
    end_time = time.time() + 10
    while display.loop_running() and time.time() < end_time:
        sprite.draw()

    logger.info("Test finished successfully.")

except Exception:
    logger.critical("Failed to initialize or run pi3d display.", exc_info=True)
finally:
    if 'display' in locals() and display:
        display.destroy()
    logger.info("Exiting test script.")
