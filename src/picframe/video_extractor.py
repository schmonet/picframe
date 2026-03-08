import os
import subprocess
import time
import shutil
import logging
from pathlib import Path
import threading
import queue
import tempfile
import signal
import shutil as shell_shutil # Rename to avoid conflict with shutil variable if used

class VideoExtractor:
    def __init__(self, temp_dir=None, step_time=10.0, pillarbox_pct=0.0, quality=6, resolution=(1920, 1080)):
        self.__logger = logging.getLogger("video_extractor.VideoExtractor")
        
        # Robust temp dir selection with fallback
        self.__temp_dir = self.__setup_temp_dir(temp_dir)
        
        self.__step_time = step_time
        self.__pillarbox_pct = pillarbox_pct
        self.__quality = quality
        self.__resolution = resolution
        self.__stop_event = threading.Event()
        self.__queued_items = set()
        self.__queue = queue.Queue()
        self.__current_process = None
        self.__current_video_path = None
        
        # Start worker thread
        self.__worker_thread = threading.Thread(target=self.__worker, daemon=True, name="VideoExtractorWorker")
        self.__worker_thread.start()

    def extract(self, video_path):
        """Queues a video for extraction."""
        self.__queued_items.add(str(video_path))
        self.__queue.put(video_path)

    def __setup_temp_dir(self, config_temp_dir):
        candidates = []
        if config_temp_dir:
            candidates.append(Path(config_temp_dir) / "picframe_video_frames")
        candidates.append(Path(tempfile.gettempdir()) / "picframe_video_frames")
        
        for path in candidates:
            try:
                if path.exists():
                    try:
                        shutil.rmtree(path)
                    except Exception as e:
                        self.__logger.warning(f"Could not clean temp dir {path}: {e}")
                path.mkdir(parents=True, exist_ok=True)
                # Test write permission
                test_file = path / ".test_write"
                test_file.touch()
                test_file.unlink()
                self.__logger.info(f"Using temporary directory: {path}")
                return path
            except Exception as e:
                self.__logger.warning(f"Failed to use temp dir {path}: {e}")
        
        raise RuntimeError("Could not create any temporary directory for video extraction.")

    def get_frames_dir(self, video_path):
        """Returns the directory where frames for the given video are stored."""
        safe_name = Path(video_path).name + "_" + str(abs(hash(str(video_path))))
        return self.__temp_dir / safe_name

    def is_in_process(self, video_path):
        return self.__current_video_path == str(video_path) or str(video_path) in self.__queued_items

    def pause(self):
        if self.__current_process and self.__current_process.poll() is None:
            self.__logger.debug("Pausing ffmpeg process.")
            self.__current_process.send_signal(signal.SIGSTOP)

    def resume(self):
        if self.__current_process and self.__current_process.poll() is None:
            self.__logger.debug("Resuming ffmpeg process.")
            self.__current_process.send_signal(signal.SIGCONT)

    def stop(self):
        self.__stop_event.set()
        if self.__current_process:
            self.__current_process.terminate()
        if self.__worker_thread.is_alive():
            self.__worker_thread.join(timeout=2.0)
        if self.__temp_dir.exists():
             shutil.rmtree(self.__temp_dir)

    def __worker(self):
        self.__logger.info("VideoExtractor worker started")
        while not self.__stop_event.is_set():
            try:
                video_path = self.__queue.get(timeout=1.0)
            except queue.Empty:
                continue

            self.__process_video(video_path)
            self.__queue.task_done()

    def __process_video(self, video_path):
        self.__current_video_path = str(video_path)
        if str(video_path) in self.__queued_items:
            self.__queued_items.remove(str(video_path))
        video_temp_dir = self.get_frames_dir(video_path)
        
        if video_temp_dir.exists():
            shutil.rmtree(video_temp_dir)
        video_temp_dir.mkdir(parents=True, exist_ok=True)

        target_width, target_height = self.__resolution

        # Check if ffmpeg is available
        if not shell_shutil.which("ffmpeg"):
            self.__logger.error("ffmpeg binary not found in PATH!")
            return

        # Improved filter chain:
        # 1. Select keyframes
        # 2. Normalize to square pixels (handle anamorphic content)
        # 3. Scale to fit within target dimensions maintaining aspect ratio
        # 4. Pad to target dimensions (centering the image)
        # 5. Set SAR to 1:1 (explicitly)
        vf_string = f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{self.__step_time})'," \
                    f"scale='trunc(iw*if(gt(sar,0),sar,1)/2)*2':'ih',setsar=1," \
                    f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease," \
                    f"pad={target_width}:{target_height}:({target_width}-iw)/2:({target_height}-ih)/2," \
                    f"setsar=1"

        command = []
        if shell_shutil.which("nice"):
            command.extend(["nice", "-n", "19"])
        if shell_shutil.which("ionice"):
            command.extend(["ionice", "-c", "3"])

        command.extend([
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error",
            "-c:v", "h264_v4l2m2m",
            "-i", str(video_path),
            "-vsync", "vfr",
            "-map", "0:v:0",
            "-vf", vf_string,
            "-q:v", str(self.__quality),
            str(video_temp_dir / "frame_%04d.jpg")
        ])

        try:
            self.__logger.debug(f"Starting extraction for {video_path}")
            self.__logger.debug(f"FFmpeg command: {' '.join(command)}")
            self.__current_process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            start_time = time.time()
            stdout, stderr = self.__current_process.communicate()
            self.__logger.debug(f"FFmpeg finished in {time.time() - start_time:.2f}s with return code {self.__current_process.returncode}")
            
            if self.__current_process.returncode != 0:
                self.__logger.error(f"ffmpeg failed for {video_path}: {stderr.decode('utf-8', errors='ignore')}")

        except Exception as e:
            self.__logger.error(f"Error extracting video {video_path}: {e}")
        finally:
            self.__current_process = None
            self.__current_video_path = None