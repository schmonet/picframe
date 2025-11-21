import os
import subprocess
import time
import re
from pathlib import Path
import sys
import json
import tempfile

TEST_IMAGE = "/home/schmali/picframe_data/data/no_pictures.jpg" # Pfad zu einem Testbild

VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpg', '.mpeg', '.m4v')

def find_videos(base_directory):
    """Findet alle Videodateien rekursiv im angegebenen Verzeichnis."""
    video_files = []
    path = Path(base_directory)
    if not path.is_dir():
        print(f"Warnung: Basis-Verzeichnis nicht gefunden: {base_directory}")
        return []
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
            capture_output=False,
            text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Fehler beim Abspielen von {filepath.name}: {e}")

def get_ddcutil_info():
    """Liest erweiterte Display-Infos (Hersteller, Modell) mit ddcutil aus."""
    try:
        result = subprocess.run(["ddcutil", "detect"], capture_output=True, text=True, check=True)
        output = result.stdout
        
        mfg_match = re.search(r"Mfg id:\s+.*? - (.*)", output)
        model_match = re.search(r"Model:\s+(.*)", output)
        year_match = re.search(r"Manufacture year:\s+(\d{4})", output)
        connector_match = re.search(r"DRM_connector:\s+.*?(\w+-\w+-\d+)", output)

        ddc_info = {}
        if mfg_match:
            ddc_info["Hersteller"] = mfg_match.group(1).strip()
        if model_match:
            ddc_info["Modell"] = model_match.group(1).strip()
        if year_match:
            ddc_info["Baujahr"] = year_match.group(1).strip()
        if connector_match:
            ddc_info["DRM_Connector"] = connector_match.group(1).strip()
        return ddc_info
    except (FileNotFoundError, subprocess.CalledProcessError):
        return {} # ddcutil nicht gefunden oder Fehler, einfach leeres Dict zurückgeben

def get_display_info():
    """Liest die aktuellen Display-Eigenschaften aus dem Kernel-Debug-Interface."""
    info_md = "### Display Eigenschaften\n\n"
    try:
        # Hole erweiterte Infos von ddcutil
        ddc_info = get_ddcutil_info()
        if ddc_info:
            info_md += "".join([f"- **{key}:** `{value}`\n" for key, value in ddc_info.items()])

        # Lese den Zustand direkt vom DRM-Treiber (zuverlässiger als modetest)
        with open("/sys/kernel/debug/dri/0/state", "r") as f:
            state_content = f.read()

        # Suche nach dem aktiven Modus (der, der eine Auflösung und Frequenz hat)
        # Wir suchen nach der letzten Zeile, die ein tatsächliches Mode-Setting enthält
        # Beispiel: mode: "1920x1080": 50 148500 ...
        mode_lines = re.findall(r"^\s*mode: \"(\d+x\d+)\": (\d+\.?\d*)\s+.*", state_content, re.MULTILINE)
        
        active_mode_found = False
        if mode_lines:
            # Nimm den letzten gefundenen Modus, da dies oft der aktive ist
            resolution, vrefresh_str = mode_lines[-1]
            vrefresh = float(vrefresh_str)
            active_mode_found = True

        # Versuche, den Connector-Namen zu finden (z.B. HDMI-A-1)
        connector_match = re.search(r"Connector \d+ \((\w+-\w+-\d+)\)", state_content)
        interface = "N/A"
        if connector_match:
            interface = connector_match.group(1)
        elif ddc_info.get("DRM_Connector"): # Fallback auf ddcutil
            interface = ddc_info.get("DRM_Connector")

        if active_mode_found:
            info_md += f"- **Display:** `{interface}`\n"
            info_md += f"- **Auflösung:** `{resolution}`\n"
            info_md += f"- **Bildwiederholrate:** `{vrefresh:.2f} Hz`\n"
        else:
            info_md += "- **Fehler:** Kein aktiver Display-Modus gefunden. Ist ein Monitor angeschlossen und aktiv?\n"
            # Schreibe den Inhalt der state-Datei in die Logdatei für Debugging-Zwecke
            with open(Path(__file__).parent / "test_bulk_video_player.log", "a") as log:
                log.write("\n--- DEBUG: /sys/kernel/debug/dri/0/state ---\n")
                log.write(state_content)
                log.write("\n--- END DEBUG ---\n")

    except FileNotFoundError as e:
        info_md += f"- **Fehler:** Debug-Interface nicht gefunden. Läuft das Skript mit `sudo`? ({e})\n"
    except Exception as e:
        info_md += f"- **Fehler:** Display-Infos konnten nicht gelesen werden. ({e})\n"
    return info_md + "\n"

def get_video_metadata(video_path):
    """Liest Metadaten wie Codec, Auflösung und Dauer mit ffprobe aus."""
    command_stream = [
        "ffprobe",
        "-v", "quiet",
        "-print_format", "json",
        "-show_streams",
        str(video_path)
    ]
    try:
        # Get stream info
        result = subprocess.run(command_stream, capture_output=True, text=True, check=True)
        metadata = json.loads(result.stdout)
        video_stream = next((s for s in metadata.get('streams', []) if s.get('codec_type') == 'video'), None)
        
        # Get frame count
        command_frames = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-count_frames", "-show_entries", "stream=nb_read_frames",
            "-of", "default=nokey=1:noprint_wrappers=1", str(video_path)
        ]
        frames_result = subprocess.run(command_frames, capture_output=True, text=True, check=True)
        frames = int(frames_result.stdout.strip())

        if video_stream:
            codec = video_stream.get('codec_name', 'N/A')            
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            duration = float(video_stream.get('duration', 0))
            
            # Extract Profile and Level
            profile = video_stream.get('profile', 'N/A')
            level = video_stream.get('level', 'N/A')
            # Format level for H.264/H.265 (e.g., 42 -> 4.2)
            if isinstance(level, int) and level > 0:
                level = str(level / 10.0)
            
            profile_level = f"{profile}@{level}" if profile != 'N/A' else "N/A"

            return f"{width}x{height}", codec, profile_level, f"{duration:.2f}s", frames
    except (FileNotFoundError, subprocess.CalledProcessError, StopIteration, json.JSONDecodeError) as e:
        print(f"Warnung: ffprobe konnte Metadaten für {video_path.name} nicht lesen: {e}")
    return "N/A", "N/A", "N/A", "N/A", 0

def test_video_playback(video_path, main_log_path):
    """Testet ein einzelnes Video und gibt die Ergebnisse zurück."""
    print(f"--- Starte Test für: {video_path.name} ---")    
    with tempfile.NamedTemporaryFile(mode='w+', delete=True, suffix='.log', prefix='mpv_') as log_file:
        # We need to suppress stdout/stderr from the subprocess to avoid the 'A: ...' lines
        # The log file will contain all necessary information.
        command = [
            "mpv",
            "--no-config",
            "--fullscreen",
            "--really-quiet", # Verhindert Statuszeilen in der Konsole
            f"--log-file={log_file.name}",
            "--msg-level=all=v", # Setzt Log-Level auf verbose, um alle Statistiken zu erfassen
            str(video_path)
        ]

        try:
            result = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                encoding='utf-8'
            )
        except FileNotFoundError:
            return "Fehler", "N/A", "N/A", "N/A", "N/A", "N/A", "mpv nicht gefunden"
        except Exception as e:
            return "Fehler", "N/A", "N/A", "N/A", "N/A", "N/A", str(e)

        # Log-Datei nach der Wiedergabe auslesen und analysieren
        log_content = log_file.read()

        # Schreibe den Inhalt des temporären Logs in die Haupt-Logdatei
        with open(main_log_path, "a") as main_log:
            main_log.write(f"--- Log for: {video_path.name} ---\n")
            main_log.write(log_content)
            main_log.write("\n--- End Log ---\n\n")

        # Reguläre Ausdrücke für die neuen Metriken
        start_ts_match = re.search(r"\[\s*(\d+\.\d+)\].+mpv \d\.\d+\.\d+ Copyright", log_content)
        end_ts_match = re.search(r"\[\s*(\d+\.\d+)\].+Exiting\.\.\.", log_content)
        playback_start_ts_match = re.search(r"\[\s*(\d+\.\d+)\].+starting audio playback", log_content)
        playback_end_ts_match = re.search(r"\[\s*(\d+\.\d+)\].+finished playback, success", log_content)
        container_fps_match = re.search(r"Container reported FPS: ([\d.]+)", log_content)
        display_fps_match = re.search(r"Display-fps: ([\d.]+)", log_content) # Neue Suche

        start_ts = float(start_ts_match.group(1)) if start_ts_match else 0.0
        end_ts = float(end_ts_match.group(1)) if end_ts_match else 0.0
        playback_start_ts = float(playback_start_ts_match.group(1)) if playback_start_ts_match else 0.0
        playback_end_ts = float(playback_end_ts_match.group(1)) if playback_end_ts_match else 0.0
        
        total_runtime = end_ts - start_ts if end_ts > start_ts else 0.0
        playback_duration = playback_end_ts - playback_start_ts if playback_end_ts > playback_start_ts else 0.0
        container_fps = float(container_fps_match.group(1)) if container_fps_match else 0.0
        display_fps = float(display_fps_match.group(1)) if display_fps_match else 0.0

        # Performance-Bewertung
        performance = "OK"
        if result.returncode != 0:
            performance = "Fehlerhaft"

        if result.returncode == 0:
            status = "OK"
            error_details = ""
        else:
            status = "Fehler"
            # Suche nach der letzten Fehlermeldung im Log
            last_error = re.findall(r"\[[a-z]+\]\s(error: .+)", log_content)
            if last_error:
                error_details = f"Exit-Code: {result.returncode}. Error: {last_error[-1]}"
            else:
                error_details = f"Exit-Code: {result.returncode}. No specific error in log."

        return status, f"{total_runtime:.2f}s", f"{playback_duration:.2f}s", performance, f"{container_fps:.2f}", f"{display_fps:.2f}", error_details

if __name__ == "__main__":
    script_dir = Path(__file__).parent
    video_base_dir = script_dir / "videos"
    videos_to_test = find_videos(video_base_dir)
    results = []

    # Display-Infos abrufen und ausgeben. Skript muss mit sudo ausgeführt werden.
    display_info = get_display_info()
    print(display_info)

    # Definiere den Pfad für die Haupt-Logdatei und leere sie zu Beginn
    main_log_path = script_dir / "test_bulk_video_player.log"
    with open(main_log_path, "w") as f:
        f.write(f"--- MPV Bulk Test Log - {time.ctime()} ---\n\n")
        f.write(display_info) # Display-Infos in die Log-Datei schreiben
    print(f"Sammle alle MPV-Logs in: {main_log_path}\n")

    for video in videos_to_test:
        # Testbild zwischen den Videos anzeigen
        if Path(TEST_IMAGE).exists():
            play_media(Path(TEST_IMAGE), duration=3)
        
        resolution, codec, profile_level, duration, frames = get_video_metadata(video)
        status, runtime, playback, perf, container_fps, display_fps, error = test_video_playback(video, main_log_path)
        
        # Berechne effektive FPS
        playback_val = float(playback.replace('s',''))
        effective_fps = frames / playback_val if playback_val > 0 else 0.0

        results.append((video.parent.name, video.name, resolution, codec, profile_level, f"{container_fps}", duration, frames, status, runtime, playback, perf, f"{effective_fps:.1f}", display_fps, error))

    # Markdown-Tabelle ausgeben
    print("\n\n--- Testergebnisse ---")
    print("| Verzeichnis | Videodatei | Auflösung | Codec | Profile@Level | MP4/FPS | Dauer | Frames | Status | Laufzeit | Playback | Performance | MPV/FPS | Display/FPS | Details |")
    print("|-------------|------------|-----------|-------|---------------|---------|--------|--------|--------|----------|----------|-------------|---------|-------------|---------|")
    for r in results:
        # r[0] bis r[14]
        print(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} | {r[11]} | {r[12]} | {r[13]} | {r[14]} |")