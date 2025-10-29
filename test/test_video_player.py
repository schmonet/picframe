import logging
import os
import time
from unittest.mock import patch, MagicMock
import glob
import subprocess

import pytest

logging.basicConfig(level=logging.DEBUG)

@pytest.fixture
def test_video_path():
    # Provide a path to a small test video file in your test directory
    test_file = os.path.join(os.path.dirname(__file__), "videos", "hd", "320x180p12_1bar_2ch_libx264_baseline_yuv420p_gop25_bit128k_max128k_buf256k_lcaac_56k_48k_2ch_eng.mp4")
    if not os.path.exists(test_file):
        pytest.skip("Test video file not found: %s" % test_file)
    return test_file

@patch("subprocess.Popen")
def test_video_player_play(mock_popen, test_video_path):
    """Test starting the video player and playing a video file."""
    # Mock the Popen instance and its stdin/stdout
    mock_proc = MagicMock()
    mock_proc.stdin = MagicMock()
    mock_proc.stdout = MagicMock()
    # Simulate the player sending state messages
    mock_proc.stdout.__iter__.return_value = iter([
        "STATE:PLAYING\n",
        "STATE:ENDED\n"
        "STATE:STOPPED\n",
    ])
    mock_proc.poll.return_value = None
    mock_popen.return_value = mock_proc

    # Import here to avoid circular import issues
    from picframe.video_streamer import VideoStreamer

    # Create the VideoStreamer and play a video
    streamer = VideoStreamer(0, 0, 320, 240, fit_display=False)
    streamer.play(test_video_path)

    # Check that the correct commands were sent to the player
    calls = [call[0][0] for call in mock_proc.stdin.write.call_args_list]
    assert any("load" in c for c in calls)

    # Simulate stopping the video
    streamer.stop()
    calls = [call[0][0] for call in mock_proc.stdin.write.call_args_list]
    assert any("stop" in c for c in calls)

    # Simulate killing the player
    streamer.kill()
    assert mock_proc.terminate.called

@pytest.mark.skipif(
    os.environ.get("GITHUB_ACTIONS") == "true",
    reason="Skipped on GitHub Actions CI"
)
def test_video_player_integration(test_video_path, caplog):
    """Test starting the video player and playing a video file."""

    caplog.set_level(logging.DEBUG)

    # Import here to avoid circular import issues
    from picframe.video_streamer import VideoStreamer

    # Create the VideoStreamer and play a video
    streamer = VideoStreamer(0, 0, 320, 240, fit_display=False)
    assert streamer.player_alive()
    streamer.play(test_video_path)
    time.sleep(3)  # Allow some time for the player to start
    streamer.pause(True)
    time.sleep(3)  # Allow some time for the player to pause
    assert streamer.is_playing() 
    streamer.pause(False)
    time.sleep(2)  # Allow some time for the player to start
    streamer.stop()
    assert streamer.is_playing() is False
    streamer.kill()
    assert streamer.player_alive() is False

def test_all_videos_compatibility(caplog):
    """
    Tests all video files in the 'videos' directory for compatibility with ffplay.
    It logs the results to 'test/video_test_results.log'.
    """
    caplog.set_level(logging.INFO)
    video_dir = os.path.join(os.path.dirname(__file__), "videos")
    # Using a tuple of extensions for endswith
    video_extensions = ('.mp4', '.mov', '.mkv', '.avi', '.ts')
    # Glob for all files and then filter by extension
    all_files = glob.glob(os.path.join(video_dir, "**", "*"), recursive=True)
    video_files = [f for f in all_files if f.lower().endswith(video_extensions)]
    
    log_file_path = os.path.join(os.path.dirname(__file__), "video_test_results.log")
    
    logging.info("Starting video compatibility test...")
    
    with open(log_file_path, "w") as log_file:
        log_file.write("---\n")
        log_file.write("Video Compatibility Test Results ---\n\n")
        
        if not video_files:
            log_file.write("No video files found to test.\n")
            logging.warning("No video files found in %s", video_dir)
            return

        for video_path in video_files:
            relative_path = os.path.relpath(video_path, video_dir)
            log_file.write(f"Testing: {relative_path}\n")
            logging.info("Testing: %s", relative_path)
            
            # Using -autoexit to prevent hangs on the last frame.
            # Using -t 5 to limit test duration per video.
            # Not using -fs to avoid freezing the Pi's console.
            command = [
                "ffplay",
                "-v", "error",
                "-an",
                "-sn",
                "-noborder",
                "-autoexit",
                "-t", "5",
                video_path
            ]
            
            try:
                # Using a generous timeout of 15 seconds.
                result = subprocess.run(command, capture_output=True, text=True, timeout=15)
                
                # ffplay with -autoexit should return 0 on success.
                if result.returncode == 0:
                    log_file.write("  -> Result: OK\n\n")
                else:
                    # This will catch crashes or other ffplay errors.
                    log_file.write(f"  -> Result: ERROR (Exit Code: {result.returncode})\n")
                    # Limit stderr to avoid huge log files
                    stderr_output = (result.stderr or "").strip()
                    if stderr_output:
                        log_file.write(f"     Stderr: {stderr_output[:500]}\n")
                    log_file.write("\n")

            except subprocess.TimeoutExpired:
                log_file.write("  -> Result: HANG (Process timed out after 15 seconds)\n\n")
            except FileNotFoundError:
                log_file.write("  -> Result: FATAL ERROR (ffplay command not found)\n\n")
                logging.critical("ffplay command not found. Please install ffmpeg.")
                break # Stop the test if ffplay is not installed
            except Exception as e:
                log_file.write(f"  -> Result: UNEXPECTED PYTHON ERROR ({e})\n\n")
            
            log_file.flush()

    logging.info("Video compatibility test finished. Results are in %s", log_file_path)