"""
This module provides a `VideoPlayer` class that manages video playback
using the command-line VLC player (`vlc`) in a subprocess.
"""
import sys
import time
import argparse
import logging
import threading
import queue
import subprocess
import os
import signal
import shlex

class VideoPlayer:
    """
    VideoPlayer manages video playback using command-line VLC.
    It communicates via stdin/stdout for commands and state, and is designed
    to be controlled by an external process (e.g., VideoStreamer).
    """

    def __init__(self, x: int, y: int, w: int, h: int, fit_display: bool = False) -> None:
        self.logger = logging.getLogger("video_player")
        self.logger.debug("Initializing VideoPlayer (VLC backend)")
        self.cmd_queue: queue.Queue[str] = queue.Queue()
        self.stdin_thread = threading.Thread(target=self._stdin_reader, daemon=True)
        self.last_state: str = ""
        self._vlc_proc: subprocess.Popen | None = None
        self.is_paused = False

    def setup(self) -> bool:
        return True

    def _send_state(self, state: str) -> None:
        if state != self.last_state:
            self.logger.info("State changed to: %s", state)
            print(f"STATE:{state}", flush=True)
            self.last_state = state

    def _stdin_reader(self):
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            self.cmd_queue.put(line)

    def _watch_vlc(self):
        if self._vlc_proc:
            self._vlc_proc.wait()
            self.logger.debug("VLC process ended.")
            self._send_state("ENDED")
            self._vlc_proc = None
            self.is_paused = False

    def run(self) -> None:
        self.stdin_thread.start()
        while True:
            try:
                line = self.cmd_queue.get(timeout=0.1)
                cmd = line.strip().split()
                if not cmd:
                    continue
                self._handle_command(cmd)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error("Error in run loop: %s", e)

    def _handle_command(self, cmd: list[str]) -> None:
        command = cmd[0]
        self.logger.debug("Handling command: %s", command)

        if command == "load" and len(cmd) > 1:
            if self._vlc_proc:
                self._vlc_proc.terminate()
                self._vlc_proc.wait()
                self._vlc_proc = None

            media_path = " ".join(cmd[1:])
            if not os.path.exists(media_path):
                self.logger.error("Media path does not exist: %s", media_path)
                return

            safe_media_path = shlex.quote(media_path)
            
            # This is the exact command the user has verified to be working.
            vlc_cmd_str = f"vlc --fullscreen --no-video-title-show --no-audio {safe_media_path} vlc://quit"

            self.logger.info("Starting VLC via shell with command: %s", vlc_cmd_str)
            try:
                self._vlc_proc = subprocess.Popen(
                    vlc_cmd_str,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    universal_newlines=True
                )
                threading.Thread(target=self._log_vlc_stderr, daemon=True).start()
                time.sleep(1)
                self._send_state("PLAYING")
                self.is_paused = False
                threading.Thread(target=self._watch_vlc, daemon=True).start()
            except FileNotFoundError:
                self.logger.critical("'vlc' command not found!")
                self._send_state("ENDED")
            except Exception as e:
                self.logger.error("Failed to start VLC: %s", e)
                self._send_state("ENDED")

        elif command == "pause":
            if self._vlc_proc and self._vlc_proc.poll() is None and not self.is_paused:
                os.kill(self._vlc_proc.pid, signal.SIGSTOP)
                self.is_paused = True

        elif command == "resume":
            if self._vlc_proc and self._vlc_proc.poll() is None and self.is_paused:
                os.kill(self._vlc_proc.pid, signal.SIGCONT)
                self.is_paused = False

        elif command == "stop":
            if self._vlc_proc and self._vlc_proc.poll() is None:
                self._vlc_proc.terminate()

    def _log_vlc_stderr(self):
        if self._vlc_proc and self._vlc_proc.stderr:
            for line in self._vlc_proc.stderr:
                self.logger.warning("[vlc]: %s", line.strip())


def main() -> None:
    parser = argparse.ArgumentParser(description="VLC Video Player for Picframe")
    parser.add_argument("--x", type=int, default=0)
    parser.add_argument("--y", type=int, default=0)
    parser.add_argument("--w", type=int, default=640)
    parser.add_argument("--h", type=int, default=480)
    parser.add_argument("--log_level", type=str, default="info", 
                        choices=["debug", "info", "warning", "error", "critical"])
    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', force=True)
    
    logger = logging.getLogger("video_player_main")
    logger.info("video_player.py (VLC/shell backend) main() started")
    
    player = VideoPlayer(args.x, args.y, args.w, args.h, fit_display=False)
    if player.setup():
        logger.info("Player setup successful. Starting run loop.")
        player.run()
    else:
        logger.error("Player setup failed.")

if __name__ == "__main__":
    main()
