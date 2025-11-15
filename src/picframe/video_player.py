import sys
import time
import argparse
import logging
import cv2
import signal

# Set up logging to stderr
logging.basicConfig(level=logging.INFO, stream=sys.stderr, format='[PLAYER] %(asctime)s - %(levelname)s - %(message)s')

# Ignore SIGPIPE and let the write call raise a BrokenPipeError instead.
# This is common in pipe-based communication.
try:
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except AttributeError:
    # Not available on Windows
    pass

def main() -> None:
    parser = argparse.ArgumentParser(description="Video Frame Streamer for Picframe")
    parser.add_argument("video_path", type=str, help="Path to the video file")
    args = parser.parse_args()

    logging.info(f"Processing video: {args.video_path}")
    try:
        cap = cv2.VideoCapture(args.video_path)
        if not cap.isOpened():
            logging.error(f"Could not open video file: {args.video_path}")
            sys.exit(1)

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if width == 0 or height == 0:
            logging.error("Video file has zero width or height. Cannot proceed.")
            sys.exit(1)

        # 1. Send header info to stdout
        print(f"WIDTH:{width}", flush=True)
        print(f"HEIGHT:{height}", flush=True)
        print(f"FPS:{fps}", flush=True)
        print(f"FRAMECOUNT:{frame_count}", flush=True)
        
        logging.info("Header sent. Starting frame streaming.")
        frame_num = 0
        # 2. Stream raw frame data to stdout
        while True:
            try:
                ret, frame = cap.read()
                if not ret:
                    logging.info(f"cap.read() returned False. End of stream after {frame_num} frames.")
                    break # End of video
                
                # Write raw frame bytes to standard output
                sys.stdout.buffer.write(frame.tobytes())
                sys.stdout.flush()
                frame_num += 1
            except BrokenPipeError:
                logging.error("Broken pipe: Parent process probably closed the pipe. Exiting.")
                break
            except Exception as e:
                logging.error(f"Error during frame read/write loop: {e}", exc_info=True)
                break # Exit loop on error
        
        logging.info("Streaming finished.")

    except Exception as e:
        logging.error(f"An error occurred: {e}", exc_info=True)
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        logging.info("Player script finished.")

if __name__ == "__main__":
    main()