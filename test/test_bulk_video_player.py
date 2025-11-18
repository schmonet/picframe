import os
import subprocess
import time
import re
from pathlib import Path
import json

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

def get_video_metadata(video_path):
    """Liest Metadaten wie Codec, Auflösung und Dauer mit ffprobe aus."""
    command = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(video_path)
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        video_stream = next((s for s in metadata.get('streams', []) if s.get('codec_type') == 'video'), None)
        if video_stream:
            codec = video_stream.get('codec_name', 'N/A')
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            duration = float(video_stream.get('duration', 0))
            return f"{width}x{height}", codec, f"{duration:.2f}s"
    except (FileNotFoundError, subprocess.CalledProcessError, StopIteration, json.JSONDecodeError) as e:
        print(f"Warnung: ffprobe konnte Metadaten für {video_path.name} nicht lesen: {e}")
    return "N/A", "N/A", "N/A"

def test_video_playback(video_path):
    """Testet ein einzelnes Video und gibt die Ergebnisse zurück."""
    print(f"--- Starte Test für: {video_path.name} ---")
    start_time = time.time()
    
    # mpv Kommando:
    # --no-config: Ignoriert lokale Konfigurationen für einen sauberen Test.
    # --fullscreen: Vollbildmodus.
    # --no-terminal: Verhindert, dass mpv die Konsole mit seinem eigenen Interface überschreibt.
    # --msg-level=all=fatal: Zeigt nur kritische Fehler an.
    # --term-status-msg=...: Gibt am Ende der Wiedergabe eine formatierte Zeile mit Statistiken aus.
    stats_format = "STATS: vo-delayed:${vo-delayed-frame-count} dropped:${dropped-frames} fps:${estimated-vo-fps}"
    command = [
        "mpv",
        "--no-config",
        "--fullscreen",
        "--no-terminal",
        "--msg-level=all=fatal",
        f"--term-status-msg={stats_format}",
        str(video_path)
    ]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        end_time = time.time()
        
        total_runtime = end_time - start_time
        
        # Extrahiere die Statistiken aus der letzten Zeile der Ausgabe
        vo_delayed = 0
        dropped_frames = 0
        estimated_fps = 0.0
        
        last_line = result.stdout.strip().split('\n')[-1]
        if "STATS:" in last_line:
            vo_delayed_match = re.search(r'vo-delayed:(\d+)', last_line)
            dropped_frames_match = re.search(r'dropped:(\d+)', last_line)
            fps_match = re.search(r'fps:([\d.]+)', last_line)
            
            if vo_delayed_match: vo_delayed = int(vo_delayed_match.group(1))
            if dropped_frames_match: dropped_frames = int(dropped_frames_match.group(1))
            if fps_match: estimated_fps = float(fps_match.group(1))
        
        if result.returncode == 0:
            status = "OK"
            error_details = ""
        else:
            status = "Fehler"
            error_details = f"Exit-Code: {result.returncode}. {result.stderr.strip()}"

        # Performance-Bewertung
        performance = "Echtzeit"
        if total_runtime > 12.0: # Wenn der gesamte Prozess > 12s für ein 10s Video braucht
            performance = "Langsam"
        if vo_delayed > 5 or dropped_frames > 5:
            performance = "Starkes Ruckeln"

        return status, f"{total_runtime:.2f}s", performance, dropped_frames, vo_delayed, f"{estimated_fps:.1f}", error_details

    except FileNotFoundError:
        return "Fehler", "N/A", "N/A", "N/A", "N/A", "N/A", "mpv oder ffprobe nicht gefunden"
    except Exception as e:
        return "Fehler", "N/A", "N/A", "N/A", "N/A", "N/A", str(e)

if __name__ == "__main__":
    videos_to_test = find_videos(VIDEO_DIRS)
    results = []

    for video in videos_to_test:
        # Testbild zwischen den Videos anzeigen
        if Path(TEST_IMAGE).exists():
            play_media(Path(TEST_IMAGE), duration=3)
        
        resolution, codec, duration = get_video_metadata(video)
        status, runtime, perf, dropped, delayed, fps, error = test_video_playback(video)
        results.append((video.name, resolution, codec, duration, status, runtime, perf, dropped, delayed, fps, error))

    # Markdown-Tabelle ausgeben
    print("\n\n--- Testergebnisse ---")
    print("| Videodatei | Auflösung | Codec | Dauer | Status | Laufzeit | Performance | Dropped | Delayed | FPS | Details |")
    print("|------------|-----------|-------|--------|--------|----------|-------------|---------|---------|-----|---------|")
    for r in results:
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} |")