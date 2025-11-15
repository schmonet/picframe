
import subprocess
import logging
import sys
import os
import numpy as np
import threading
from typing import Optional

class FFmpegStreamer:
    """
    Uses ffprobe to get video metadata and ffmpeg to decode video frames,
    streaming them as raw bytes to stdout, which are then read by this class.
    This leverages hardware acceleration in ffmpeg for performance.
    """
    def __init__(self, video_path: str, ffprobe_path: str = 'ffprobe'):
        self.logger = logging.getLogger("FFmpegStreamer")
        self.logger.info(f"Initializing for video: {video_path}")

        if not os.path.exists(video_path):
            raise IOError(f"Could not find video file: {video_path}")

        self._proc = None
        self.width = 0
        self.height = 0
        self.fps = 30.0 # Default
        self.frame_size = 0
        self._is_running = False

        try:
            self._get_video_info(video_path, ffprobe_path)
            self._start_ffmpeg_stream(video_path)
            self._is_running = True
        except Exception as e:
            self.logger.error("Failed to initialize FFmpegStreamer: %s", e, exc_info=True)
            self.stop()

    def _get_video_info(self, video_path: str, ffprobe_path: str):
        command = [
            ffprobe_path,
            '-v', 'error',
            '-select_streams', 'v:0',
            '-show_entries', 'stream=width,height,avg_frame_rate',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            video_path
        ]
        self.logger.info(f"Running ffprobe with command: {' '.join(command)}")
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=True)
            output = result.stdout.strip().split('\n')
            self.width = int(output[0])
            self.height = int(output[1])
            
            # Evaluate frame rate fraction (e.g., '25/1')
            if '/' in output[2]:
                num, den = map(int, output[2].split('/'))
                self.fps = num / den if den != 0 else 30.0
            else:
                self.fps = float(output[2])

            self.frame_size = int(self.width * self.height * 1.5) # 1 byte for Y, 0.25 for U, 0.25 for V
            self.logger.info(f"Video info from ffprobe: {self.width}x{self.height} @ {self.fps:.2f} FPS")
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError, ValueError) as e:
            self.logger.error(f"ffprobe failed: {e}. Using default 1920x1080@30fps.")
            # Fallback to reasonable defaults if ffprobe fails
            self.width, self.height, self.fps = 1920, 1080, 30.0
            self.frame_size = int(self.width * self.height * 1.5)

    def _log_stderr(self):
        if self._proc and self._proc.stderr:
            for line in iter(self._proc.stderr.readline, b''):
                self.logger.warning("[ffmpeg]: %s", line.decode().strip())

    def _start_ffmpeg_stream(self, video_path: str):
        command = [
            'ffmpeg',
            '-hwaccel', 'drm',
            '-c:v', 'h264_v4l2m2m',
            '-nostdin',
            '-i', video_path,
            '-f', 'image2pipe',
            '-pix_fmt', 'yuv420p',
            '-vcodec', 'rawvideo',
            '-' # Output to stdout
        ]
        self.logger.info(f"Starting ffmpeg stream with command: {' '.join(command)}")
        self._proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Start a thread to monitor stderr from ffmpeg
        stderr_thread = threading.Thread(target=self._log_stderr, daemon=True)
        stderr_thread.start()

    def get_frame(self) -> Optional[np.ndarray]:
        if not self._is_running or not self._proc or not self._proc.stdout:
            return None

        try:
            frame_bytes = self._proc.stdout.read(self.frame_size)
            if len(frame_bytes) < self.frame_size:
                self.logger.info("End of ffmpeg stream detected.")
                self.stop()
                return None

            frame = np.frombuffer(frame_bytes, dtype=np.uint8)
            return frame
        except Exception as e:
            self.logger.error("Error reading frame from ffmpeg pipe: %s", e)
            self.stop()
            return None

    def stop(self):
        self.logger.info("Stopping ffmpeg stream.")
        self._is_running = False
        if self._proc:
            if self._proc.poll() is None:
                self._proc.terminate()
                self._proc.wait()
            self._proc = None

    def is_running(self) -> bool:
        return self._is_running and self._proc is not None and self._proc.poll() is None
