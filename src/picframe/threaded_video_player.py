
import cv2
import threading
import queue
import logging

class ThreadedVideoPlayer:
    """
    Decodes a video file in a separate thread and puts the frames into a queue.
    This avoids blocking the main thread and prevents hardware access conflicts.
    """
    def __init__(self, video_path: str, queue_size: int = 100):
        self.logger = logging.getLogger("ThreadedVideoPlayer")
        self.logger.info(f"Initializing for video: {video_path}")

        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise IOError(f"Could not open video file: {video_path}")

        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

        self.frame_queue = queue.Queue(maxsize=queue_size)
        self._is_running = True
        self.reader_thread = threading.Thread(target=self._reader, daemon=True)
        self.reader_thread.start()
        self.logger.info(f"Video properties: {self.width}x{self.height} @ {self.fps:.2f} FPS")

    def _reader(self):
        """The loop that runs in the background thread."""
        try:
            while self._is_running:
                if self.frame_queue.full():
                    # Avoid busy-waiting if the queue is full
                    threading.Event().wait(0.01)
                    continue

                ret, frame = self.cap.read()
                if not ret:
                    # End of video
                    break
                
                self.frame_queue.put(frame)
        except Exception as e:
            self.logger.error(f"Error in reader thread: {e}", exc_info=True)
        finally:
            # Signal that the stream has ended by putting a sentinel value
            self.frame_queue.put(None)
            self.cap.release()
            self.logger.info("Reader thread finished.")

    def get_frame(self, block: bool = False):
        """Retrieves a frame from the queue."""
        try:
            # Use get_nowait for non-blocking, or get for blocking
            return self.frame_queue.get(block=block)
        except queue.Empty:
            return None # Return None if the queue is empty and not blocking

    def stop(self):
        """Stops the reader thread gracefully."""
        self.logger.info("Stopping video player thread...")
        self._is_running = False
        # Wait for the thread to finish
        self.reader_thread.join()
        self.logger.info("Video player stopped.")

    def is_running(self) -> bool:
        """
        Checks if the reader thread is alive. The stream might still have frames
        in the queue even after the reader thread has finished.
        """
        return self.reader_thread.is_alive()
