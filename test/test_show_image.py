import pi3d
import time
import sys
import os
from PIL import Image

def main():
    if len(sys.argv) != 3:
        print("Usage: python test_show_image.py <image_path> <duration_seconds>")
        sys.exit(1)

    image_path = sys.argv[1]
    duration = int(sys.argv[2])

    print("Initializing display...")
    # Match viewer_display's create options
    display = pi3d.Display.create(
        use_sdl2=True, # Use SDL2
        background=(0.0, 0.0, 0.0, 1.0), # Black background
        frames_per_second=20,
        display_config=pi3d.DISPLAY_CONFIG_HIDE_CURSOR | pi3d.DISPLAY_CONFIG_NO_FRAME,
        use_glx=False # Explicitly disable GLX, rely on SDL2/EGL
    )
    print(f"Display created: {display.width}x{display.height}")

    if not display.is_running:
        print("Display creation failed!")
        return

    shader = pi3d.Shader("uv_flat")
    camera = pi3d.Camera(is_3d=False)
    slide = pi3d.Sprite(camera=camera, w=display.width, h=display.height, z=5.0)

    print(f"Loading image with PIL: {image_path}")
    try:
        # Load image using PIL, which is more robust
        pil_image = Image.open(image_path)
    except Exception as e:
        print(f"Error loading image with PIL: {e}")
        display.destroy()
        return

    print("Creating pi3d.Texture from PIL image")
    # Create pi3d Texture from the PIL image object
    tex = pi3d.Texture(pil_image, blend=True, m_repeat=False, free_after_load=True)
    
    if not tex:
        print("pi3d.Texture creation failed!")
        display.destroy()
        return

    slide.set_draw_details(shader, [tex])
    
    print("Entering render loop...")
    start_time = time.time()
    while display.loop_running() and (time.time() - start_time < duration):
        slide.draw()
        # The loop_running() call with a set fps should handle timing.
        # A short sleep can prevent 100% CPU usage if vsync is not working.
        time.sleep(0.01) 

    print("Loop finished. Destroying display.")
    display.destroy()
    print("Done.")

if __name__ == "__main__":
    main()