import time
import os
import sys
import logging
import pi3d
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from picframe.video_streamer import FFmpegStreamer

# --- Configuration ---
VIDEO_PATH = "/home/schmali/picframe/test/videos/hd/1280x720p25_6bar_2ch_libx264_high_yuv420p_gop50_bit2500k_max2500k_buf7M_lcaac_192k_48k_2ch_eng.mp4"
SHADER_PATH = "/home/schmali/picframe/src/picframe/data/shaders/yuv"

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

def main():
    logging.info("Starting YUV FFmpeg video test...")

    # 1. Initialize pi3d Display
    display = pi3d.Display.create(use_sdl2=True, background=(0.0, 0.0, 0.0, 1.0), frames_per_second=30)
    logging.info(f"Display created: {display.width}x{display.height}")
    if not display.is_running:
        logging.error("Display creation failed! Exiting.")
        return

    # 2. Initialize FFmpegStreamer
    try:
        streamer = FFmpegStreamer(VIDEO_PATH)
    except Exception as e:
        logging.error(f"FFmpegStreamer failed to initialize: {e}")
        display.destroy()
        return

    display.frames_per_second = streamer.fps

    # 3. Load the YUV shader
    yuv_shader = pi3d.Shader(SHADER_PATH)
    slide = pi3d.Sprite(camera=pi3d.Camera(is_3d=False), w=display.width, h=display.height, z=5.0)

    # 4. Create textures for Y, U, and V planes
    w, h = streamer.width, streamer.height
    y_tex = pi3d.Texture(np.zeros((h, w, 1), dtype=np.uint8), blend=False, m_repeat=False, free_after_load=False, mipmap=False)
    u_tex = pi3d.Texture(np.zeros((h // 2, w // 2, 1), dtype=np.uint8), blend=False, m_repeat=False, free_after_load=False, mipmap=False)
    v_tex = pi3d.Texture(np.zeros((h // 2, w // 2, 1), dtype=np.uint8), blend=False, m_repeat=False, free_after_load=False, mipmap=False)
    
    slide.set_draw_details(yuv_shader, [y_tex, u_tex, v_tex])

    logging.info("Entering main render loop...")
    frame_count = 0
    start_time = time.time()

    # 5. Main Loop
    while display.loop_running():
        frame_yuv = streamer.get_frame()

        if frame_yuv is not None:
            # Update the textures with the new YUV plane data
            y_plane = frame_yuv[0:(w*h)].reshape(h, w, 1)
            u_plane = frame_yuv[(w*h):(w*h) + (w*h//4)].reshape(h//2, w//2, 1)
            v_plane = frame_yuv[(w*h) + (w*h//4):].reshape(h//2, w//2, 1)

            y_tex.update_ndarray(y_plane)
            u_tex.update_ndarray(u_plane)
            v_tex.update_ndarray(v_plane)
            
            frame_count += 1
        elif not streamer.is_running():
            logging.info("Video stream finished.")
            break

        slide.draw()

    end_time = time.time()
    logging.info("Render loop finished.")

    # 6. Clean up
    streamer.stop()
    display.destroy()

    # 7. Report results
    duration = end_time - start_time
    if duration > 0:
        actual_fps = frame_count / duration
        logging.info(f"Played {frame_count} frames in {duration:.2f} seconds ({actual_fps:.2f} FPS).")
    else:
        logging.info("Render loop did not run or ran too briefly.")

    logging.info("Test finished.")

if __name__ == "__main__":
    main()
