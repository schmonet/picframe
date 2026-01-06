import os
import subprocess
import time
import argparse
import re
from pathlib import Path

import tempfile
import shutil
import pi3d
from PIL import Image
import sys
import io
import signal
import shlex

TEST_IMAGE = "/home/schmali/picframe_data/data/no_pictures.jpg" # Pfad zu einem Testbild

VIDEO_EXTENSIONS = ('.mp4', '.mov', '.avi', '.mkv', '.webm', '.mpg', '.mpeg', '.m4v', '.ts', '.m2ts')

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

def play_image(filepath, duration=5):
    """Zeigt ein Bild für eine bestimmte Dauer mit mpv an."""
    print(f"\nZeige Bild '{filepath.name}' für {duration:.2f} Sekunden...")
    try:
        # --image-display-duration ist nötig, damit mpv bei einem Bild nicht sofort beendet
        subprocess.run(
            ["mpv", "--fullscreen", "--quiet", f"--image-display-duration={duration}", str(filepath)],
            check=True,
            capture_output=True,
            text=True
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Fehler beim Anzeigen von {filepath.name}: {e}")

def process_video_as_slideshow(display, slide, shader, video_path, step_time, time_delay, fade_time, temp_base_dir, last_texture=None, pillar_box_pct=0.0):
    """Extrahiert Frames aus einem Video und zeigt sie als Diashow an."""
    print(f"\n--- Verarbeite Video '{video_path.name}' als Slideshow ---")

    # Erstelle ein temporäres Verzeichnis für die Frames dieses Videos
    video_temp_dir = Path(tempfile.mkdtemp(dir=temp_base_dir))

    # Use display dimensions for scaling
    dw, dh = int(display.width), int(display.height)
    # Ensure even dimensions for ffmpeg
    if dw % 2 != 0: dw -= 1
    if dh % 2 != 0: dh -= 1

    # Construct the filter string as a single string variable to ensure correct concatenation
    vf_string = (f"select='isnan(prev_selected_t)+gte(t-prev_selected_t,{step_time})',"
                 f"scale='trunc(iw*if(gt(sar,0),sar,1)/2)*2':'ih',setsar=1,"
                 f"scale={dw}:{dh}:force_original_aspect_ratio=decrease,"
                 f"pad={dw}:{dh}:({dw}-iw)/2:({dh}-ih)/2,"
                 f"setsar=1")

    try:
        # ffmpeg Kommando zum Extrahieren von Frames als JPG-Dateien, basierend auf dem
        # auf dem Zielsystem verifizierten Befehl.
        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel", "error", # Weniger Output im Normalbetrieb
            "-c:v", "h264_v4l2m2m",
            "-i", str(video_path),
            "-vsync", "vfr",
            "-map", "0:v:0",
            # Der -vf String muss die ' enthalten, damit der ffmpeg-Parser die Kommas
            # in den if() Ausdrücken korrekt interpretiert.
            # Der Filter wählt Keyframes mit einem Mindestabstand aus und skaliert sie (bilinear für Speed).
            "-vf", vf_string,
            "-q:v", "6", # Qualität angepasst (8->6)
            str(video_temp_dir / "frame_%04d.jpg")
        ]

        # Starte ffmpeg im Hintergrund (Popen statt run), schreibt direkt auf die SD-Karte
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,   # stdin explizit schließen
            stdout=subprocess.DEVNULL,  # stdout ignorieren (ffmpeg schreibt Dateien)
            stderr=subprocess.PIPE,     # stderr pipe für Fehlerfall
        )

        def get_frame_path(i):
            return video_temp_dir / f"frame_{i:04d}.jpg"

        print("Warte auf erste Frames...")
        # Wir warten auf Frame 2, um sicherzugehen, dass Frame 1 fertig geschrieben ist
        while not get_frame_path(2).exists():
            if process.poll() is not None:
                break # Prozess beendet
            time.sleep(0.1)

        first_frame_path = get_frame_path(1)
        
        if not first_frame_path.exists():
            print(f"ffmpeg Fehler oder keine Frames bei '{video_path.name}'")
            _, stderr = process.communicate()
            print(stderr.decode('utf-8', errors='ignore'))
            return
        
        # Diagnose: Prüfe die Dimensionen des erzeugten Bildes
        with Image.open(first_frame_path) as img:
            # print(f"Generiertes Bild 1: {img.size}")
            if img.size != (dw, dh):
                print(f"WARNUNG: Bildgröße {img.size} entspricht nicht der Zielauflösung {dw}x{dh}!")

        print("Starte pi3d Anzeige...")

        # Lade das erste Bild als Hintergrund (pi3d lädt Datei vom Pfad)
        tex_b = pi3d.Texture(str(first_frame_path), blend=True, m_repeat=False, mipmap=False, free_after_load=True)
        
        # Setze alle Shader-Uniforms auf Standardwerte zurück, um Artefakte zu vermeiden
        # (genau wie in der Hauptanwendung viewer_display.py)
        slide.unif[42] = 1.0 # Scale X tex0
        slide.unif[43] = 1.0 # Scale Y tex0
        slide.unif[45] = 1.0 # Scale X tex1
        slide.unif[46] = 1.0 # Scale Y tex1
        slide.unif[48] = 0.0 # Offset X tex0
        slide.unif[49] = 0.0 # Offset Y tex0
        slide.unif[51] = 0.0 # Offset X tex1
        slide.unif[52] = 0.0 # Offset Y tex1
        slide.unif[55] = 1.0
        slide.unif[50] = 1.0 # Scale tex0 (legacy)
        slide.unif[53] = 1.0 # Scale tex1 (legacy)
        slide.unif[54] = 0.0 # Setze Blend-Modus auf 'mix' (unif[18][0] -> index 54)
        slide.unif[47] = 1.0 # Setze Rand-Transparenz auf undurchsichtig (unif[15][2] -> index 47)

        if last_texture is not None:
            slide.set_draw_details(shader, [last_texture, tex_b])
            slide.unif[44] = 1.0
            print(f"  -> Überblenden vom vorherigen Video für {fade_time:.2f}s")
            start_time = time.time()
            while True:
                t = time.time() - start_time
                if t > fade_time:
                    break
                if not display.loop_running():
                    process.terminate()
                    return
                blend = t / fade_time
                slide.unif[44] = 1.0 - blend
                slide.draw()
            slide.unif[44] = 0.0
            slide.draw()
        else:
            slide.set_draw_details(shader, [tex_b, tex_b]) # Zeige zuerst nur das erste Bild
            # Setze den Blend-Wert auf 1.0 (100% Vordergrund) (unif[14][2] -> index 44)
            slide.unif[44] = 1.0

        current_idx = 1
        ffmpeg_paused = False

        while True:
            # 1. Halte das aktuelle Bild (tex_b)
            print(f"  -> Halte Frame {current_idx} für {time_delay:.2f}s")
            start_time = time.time()
            while (time.time() - start_time) < time_delay:
                if not display.loop_running():
                    if ffmpeg_paused:
                        process.send_signal(signal.SIGCONT)
                    process.terminate()
                    return
                slide.draw()

            # 2. Bereite nächsten Frame vor
            next_idx = current_idx + 1
            next_path = get_frame_path(next_idx)
            lookahead_path = get_frame_path(next_idx + 1)

            # Warte auf den nächsten Frame (wir schauen eins voraus, um sicher zu sein, dass der nächste fertig ist)
            while True:
                if lookahead_path.exists():
                    break # Nächster Frame ist sicher fertig
                
                # Wenn wir auf einen Frame warten und ffmpeg pausiert ist, müssen wir es aufwecken!
                if ffmpeg_paused:
                    process.send_signal(signal.SIGCONT)
                    ffmpeg_paused = False

                if process.poll() is not None:
                    # Prozess beendet, wir nehmen was da ist
                    if not next_path.exists():
                        # Ende der Slideshow
                        shutil.rmtree(video_temp_dir)
                        return tex_b
                    break

                if not display.loop_running():
                    if ffmpeg_paused:
                        process.send_signal(signal.SIGCONT)
                    process.terminate()
                    shutil.rmtree(video_temp_dir)
                    return
                slide.draw() # Zeichne weiter das aktuelle Bild während wir warten

            # Nächster Frame ist bereit
            tex_f = tex_b
            tex_b = pi3d.Texture(str(next_path), blend=True, m_repeat=False, mipmap=False, free_after_load=True)
            
            slide.set_draw_details(shader, [tex_f, tex_b])
            slide.unif[44] = 1.0 # Beginne mit 100% Vordergrund (altes Bild)

            # 3. Überblenden
            print(f"  -> Überblenden für {fade_time:.2f}s")
            start_time = time.time()
            while True:
                t = time.time() - start_time
                if t > fade_time:
                    break
                if not display.loop_running():
                    if ffmpeg_paused:
                        process.send_signal(signal.SIGCONT)
                    process.terminate()
                    return
                
                blend = t / fade_time
                slide.unif[44] = 1.0 - blend # Animiere den Blend-Wert
                slide.draw()
            
            # Stelle sicher, dass der Blend-Wert sauber auf 0.0 ist, bevor wir die Textur löschen
            slide.unif[44] = 0.0
            slide.draw()

            # 4. Aufräumen: Lösche alte Datei von der SD-Karte, um Platz zu sparen
            try:
                os.remove(get_frame_path(current_idx))
            except OSError:
                pass

            # Throttling: Pausiere ffmpeg, wenn zu viele Frames im Voraus produziert wurden
            if process.poll() is None:
                # Wenn 5 Frames Vorsprung existieren -> Pause, um RAM/IO zu schonen
                if get_frame_path(current_idx + 5).exists() and not ffmpeg_paused:
                    process.send_signal(signal.SIGSTOP)
                    ffmpeg_paused = True
                # Wenn nur noch 2 Frames Vorsprung existieren -> Weiter
                elif not get_frame_path(current_idx + 2).exists() and ffmpeg_paused:
                    process.send_signal(signal.SIGCONT)
                    ffmpeg_paused = False

            current_idx += 1

    except (FileNotFoundError, Exception) as e:
        print(f"Fehler bei der Verarbeitung von {video_path.name}: {e}")
        if 'video_temp_dir' in locals() and video_temp_dir.exists():
             shutil.rmtree(video_temp_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Testet eine Video-Slideshow für PicFrame.")
    parser.add_argument(
        '--video-slideshow-step-time',
        type=float,
        default=2.0,
        help="Sekunden zwischen den zu extrahierenden Keyframes. Standard: 2.0"
    )
    parser.add_argument(
        '--video-slideshow-time-delay',
        type=float,
        default=9.0,
        help="Anzeigedauer für jeden extrahierten Frame. Standard: 9.0"
    )
    parser.add_argument(
        '--video-slideshow-fade-time',
        type=float,
        default=1.0,
        help="Überblendzeit zwischen den extrahierten Frames. Standard: 1.0"
    )
    parser.add_argument(
        '--temp-dir',
        type=str,
        default=None,
        help="Verzeichnis für temporäre Dateien (z.B. /mnt/usb/temp). Standard: ./temp_frames"
    )
    parser.add_argument(
        '--pillar-box-pct',
        type=float,
        default=0.0,
        help="Prozentualer Anteil des schwarzen Randes an jeder Seite (0.0-0.5). Standard: 0.0"
    )

    args = parser.parse_args()

    # Finde das 'videos' Verzeichnis relativ zum Speicherort des Skripts
    script_dir = Path(__file__).parent
    video_base_dir = script_dir / "videos"

    videos_to_test = find_videos(video_base_dir)

    # Basisverzeichnis für temporäre Frame-Ordner
    if args.temp_dir:
        temp_base_dir = Path(args.temp_dir)
    else:
        temp_base_dir = script_dir / "temp_frames"
    temp_base_dir.mkdir(parents=True, exist_ok=True)
    if not videos_to_test:
        print("Keine Videos in den angegebenen Verzeichnissen gefunden. Test wird beendet.")
        exit()

    # Initialisiere pi3d
    display = pi3d.Display.create(use_sdl2=True, background=(0.2, 0.2, 0.2, 1.0))
    if not display.is_running:
        print("pi3d Display konnte nicht initialisiert werden. Test wird beendet.")
        exit()
    print(f"Display initialisiert: {display.width}x{display.height}")
    
    # Lade den Blend-Shader. Der Pfad muss relativ zum Ausführungsort sein.
    # Wir gehen davon aus, dass das Skript aus dem 'test'-Verzeichnis gestartet wird.
    shader_path = script_dir.parent / "src" / "picframe" / "data" / "shaders" / "blend_new"

    # Definiere einen Vertex-Shader, der die Textur-Koordinaten für tex0 und tex1 berechnet.
    # Dies ist notwendig, falls blend_new.vs fehlt oder nicht geladen wird, da der Standard-VS
    # texcoordoutf/b nicht bereitstellt. Diese Version entspricht der Logik der Hauptanwendung.
    vshader_source = """
attribute vec3 vertex;
attribute vec2 texcoord;
uniform mat4 modelviewmatrix[2];
uniform vec3 unib[5];
uniform vec3 unif[20];
varying vec2 texcoordoutf;
varying vec2 texcoordoutb;
varying float dist;
varying float fog_start;
varying float is_3d;
void main(void) {
  gl_Position = modelviewmatrix[1] * vec4(vertex, 1.0);
  // tex0 (foreground) uses unif[14] for scale and unif[16] for offset
  texcoordoutf = texcoord * vec2(unif[14].x, unif[14].y) + unif[16].xy;
  // tex1 (background) uses unif[15] for scale and unif[17] for offset
  texcoordoutb = texcoord * vec2(unif[15].x, unif[15].y) + unif[17].xy;
  dist = gl_Position.z;
  fog_start = unib[1].y;
  is_3d = unib[2].z;
}
"""
    shader = pi3d.Shader(shfile=str(shader_path), vshader_source=vshader_source)
    camera = pi3d.Camera(is_3d=False)
    slide = pi3d.Sprite(camera=camera, w=display.width, h=display.height, z=5.0)
    slide.set_shader(shader)

    try:
        last_tex = None
        # Berechne die Zeiten basierend auf den Argumenten
        for video in videos_to_test:
            # Anstatt das Video direkt abzuspielen, verarbeiten wir es zu einer Slideshow
            last_tex = process_video_as_slideshow(
                display,
                slide,
                shader,
                video,
                step_time=args.video_slideshow_step_time,
                time_delay=args.video_slideshow_time_delay,
                fade_time=args.video_slideshow_fade_time,
                temp_base_dir=temp_base_dir,
                last_texture=last_tex,
                pillar_box_pct=args.pillar_box_pct)
            if not display.is_running:
                break # Schleife verlassen, wenn Fenster geschlossen wurde

    except KeyboardInterrupt:
        print("\nSkript durch Benutzer abgebrochen.")
    except Exception as e:
        print(f"Ein unerwarteter Fehler ist aufgetreten: {e}")
    finally:
        if args.temp_dir is None and temp_base_dir.exists():
            shutil.rmtree(temp_base_dir) # Aufräumen am Ende
        display.destroy()
        print("\n--- Test der Video-zu-Bild-Extraktion und Anzeige abgeschlossen. ---")