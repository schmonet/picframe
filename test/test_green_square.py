import time
import os
import sys
import logging
import pi3d

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    logging.info("Starting green square test with built-in shader...")

    # 1. Initialize pi3d Display
    display = pi3d.Display.create(use_sdl2=True, background=(0.0, 0.0, 1.0, 1.0), frames_per_second=30)
    logging.info(f"Display created: {display.width}x{display.height}")
    if not display.is_running:
        logging.error("Display creation failed! Exiting.")
        return

    # 2. Load a built-in shader
    shader = pi3d.Shader("mat_flat")
    logging.info("Built-in shader 'mat_flat' loaded.")

    # 3. Create a sprite
    sprite = pi3d.Sprite(camera=pi3d.Camera(is_3d=False), w=display.width, h=display.height, z=5.0)
    sprite.set_draw_details(shader, []) # Assign shader
    sprite.set_material((0.0, 1.0, 0.0)) # Set material to green
    logging.info("Sprite created and configured with green material.")

    logging.info("Entering main render loop...")
    
    # 4. Main Loop - run for 5 seconds
    start_time = time.time()
    while display.loop_running() and (time.time() - start_time) < 5.0:
        sprite.draw()

    logging.info("Render loop finished.")

    # 5. Clean up
    display.destroy()
    logging.info("Test finished.")

if __name__ == "__main__":
    main()