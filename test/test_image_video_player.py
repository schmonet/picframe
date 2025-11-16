import os
import subprocess
import time
import re
from pathlib import Path

VIDEO_DIRS = [
    "/home/schmali/picframe/test/videos/ext/",
    "/home/schmali/picframe/test/videos/hd/",
    "/home/schmali/picframe/test/videos/hdr/",
]

TEST_IMAGE = "/home/schmali/picframe_data/data/no_pictures.jpg" # Pfad zu einem Testbild

VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpg', '.mpeg', '.m4v')

def find_videos(directories):
    """Findet alle Videodateien in den angegebenen Verzeichnissen."""
    video_files = []
    for directory in directories:
        path = Path(directory)
        if not path.is_dir():
            print(f"Warnung: Verzeichnis nicht gefunden: {directory}")
            continue
        for root, _, files in os.walk(path):
            for file in files:
                if file.lower().endswith(VIDEO_EXTENSIONS):
                    video_files.append(Path(root) / file)
    return sorted(video_files)

def play_media(filepath, duration=5):
    """Spielt eine Medien-Datei mit mpv ab."""
    print(f"\nSpiele '{filepath.name}' für {duration} Sekunden...")
    try:
        subprocess.run(
            ["mpv", "--fullscreen", f"--length={duration}", str(filepath)],
            check=True,
            capture_output=True,
            text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Fehler beim Abspielen von {filepath.name}: {e}")

def test_video_playback(video_path):
    """Testet ein einzelnes Video und gibt die Ergebnisse zurück."""
    print(f"--- Starte Test für: {video_path.name} ---")
    start_time = time.time()
    
    # mpv Kommando: --no-config, um lokale Konfigs zu ignorieren, --quiet für saubere Ausgabe
    command = ["mpv", "--no-config", "--quiet", "--fullscreen", str(video_path)]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        end_time = time.time()
        
        playback_time = end_time - start_time
        
        # Suche nach "Dropped frames" in der Ausgabe von mpv
        dropped_frames_match = re.search(r'Dropped frames: (\d+)', result.stderr)
        dropped_frames = int(dropped_frames_match.group(1)) if dropped_frames_match else 0
        
        if result.returncode == 0:
            status = "OK"
            error_details = ""
        else:
            status = "Fehler"
            error_details = f"Exit-Code: {result.returncode}"

        # Performance-Bewertung
        # Annahme: Videos sind ca. 10s lang. Wenn es > 12s dauert, ist es nicht mehr Echtzeit.
        performance = "Echtzeit"
        if playback_time > 12.0:
            performance = "Langsam"
        if dropped_frames > 5: # Ein paar wenige sind oft ok, aber viele deuten auf Probleme hin
            performance = "Starkes Ruckeln"

        return status, f"{playback_time:.2f}s", performance, dropped_frames, error_details

    except FileNotFoundError:
        return "Fehler", "N/A", "N/A", "N/A", "mpv nicht gefunden"
    except Exception as e:
        return "Fehler", "N/A", "N/A", "N/A", str(e)

if __name__ == "__main__":
    videos_to_test = find_videos(VIDEO_DIRS)
    results = []

    for video in videos_to_test:
        # Testbild zwischen den Videos anzeigen
        if Path(TEST_IMAGE).exists():
            play_media(Path(TEST_IMAGE), duration=3)
        
        status, playback_time, performance, dropped, error = test_video_playback(video)
        results.append((video.name, status, playback_time, performance, dropped, error))

    # Markdown-Tabelle ausgeben
    print("\n\n--- Testergebnisse ---")
    print("| Videodatei | Status | Wiedergabezeit | Performance | Dropped Frames | Details |")
    print("|------------|--------|----------------|-------------|----------------|---------|")
    for r in results:
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")