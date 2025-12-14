## 2023-11-11

## README.md
- Enthält eine allgemeine Beschreibung des Projekts, eine Liste der wichtigsten Funktionen und einen Verweis auf die Wiki-Dokumentation.  
- **Neu:** Abschnitt *Fork Information* mit den wichtigsten Änderungen in diesem Fork und den Mitwirkenden (Martin Schmalohr, Google's Gemini).

## change.log
- Protokolliert alle durchgeführten und geplanten Änderungen am Projekt, gruppiert nach Datum.

## TODO.md
- Diese Datei.  
- Enthält eine fortlaufend aktualisierte Funktionsbeschreibung aller geänderten oder hinzugefügten Dateien.

## src/picframe/model.py
- Erweiterung der Kernlogik von picframe.
- **`group_by_dir: True`**  
  - Zeigt alle Fotos aus einem zufällig gewählten Album-Ordner, bevor ein neuer gewählt wird.  
  - Verhindert Wiederholungen durch Abgleich mit `shown_albums.log`.  
  - Passt `shuffle` so an, dass nur innerhalb des Ordners gemischt wird.
- **`delete_after_show: True`**  
  - Löscht jede Bilddatei unmittelbar nach der Anzeige endgültig vom Speichermedium.  
- **`shown_albums.log`**  
  - Log-Datei mit den Pfaden aller bereits gezeigten Alben.  
  - Verhindert erneute Auswahl durch `group_by_dir`.

## src/picframe/config/configuration_example.yaml
- Aktualisierte Beispiel-Konfiguration mit den neuen Optionen `group_by_dir` und `delete_after_show`.
- **Neu:** Die Ken Burns-Konfiguration wurde um die neuen Parameter `kenburns_landscape_wobble_pct` und `kenburns_portrait_wobble_pct` erweitert und der veraltete `kenburns_wobble_pct` wurde auskommentiert.

## src/picframe/interface_mqtt.py
- **Korrektur:** Behebt `TypeError` beim Start durch Inkompatibilität mit älteren Python-Versionen.  
- Typ-Hinweise wurden auf `Union` aus dem `typing`-Modul umgestellt.

## src/picframe/viewer_display.py
- **Korrektur:** Ken-Burns-Effekt (Schwenken/Zoomen) wird im Pausenmodus korrekt angehalten.
- **Neu:** `kenburns_wobble_pct` wurde aufgeteilt in `kenburns_landscape_wobble_pct` und `kenburns_portrait_wobble_pct`, um eine separate Steuerung für Quer- und Hochformatbilder zu ermöglichen.
- Erweiterung des Ken Burns effekts, wenn `kenburns: true`
    - Ken Burns zum nächsten Bild startet bereits während der Überblendung
    - **Alle:** Unabhängig von Bildformat
        - wenn `kenburns_random_pan: true` für jedes Bild zufällige seitliche drift (pan) stattfindet. Die maximale Stärke des Pans wird für Querformatbilder durch `kenburns_landscape_wobble_pct` und für Hochformatbilder durch `kenburns_portrait_wobble_pct` gesteuert.
        - wenn `kenburns_random_pan: false` zentrierter zoom ohne seitliche drift
    - **Landscape:** Wenn *Bild-Breite ≥ Höhe*
        - Wenn `kenburns_zoom_direction: random` für jedes Bild zufällig, `zoom: in` oder `zoom: out` und zoom percentage zufällig ≤ `kenburns_zoom_pct`
        - Wenn `kenburns_zoom_direction: in, out` für jedes Bild gleich, entsprechend `zoom: in` oder `zoom: out` und zoom percentage zufällig = `kenburns_zoom_pct`
        - **Neu:** Die Berechnung für den Pan/Wobble-Effekt basiert nun auf den Display-Dimensionen anstatt auf dem Bild-Überschuss. Dies sorgt für einen sichtbareren und konsistenteren Effekt.
        - **Korrektur:** Die Berechnung des Pan-Bereichs wurde korrigiert, um schwarze Ränder zu Beginn/Ende des Zooms zu verhindern. Der erlaubte Pan-Bereich wird nun für den Start- und End-Zoom-Level separat berechnet.
    - **Portrait:** Wenn *Bild-Breite ≤ Höhe*
        - Wenn `kenburns_scroll_direction: random` für jedes Bild zufällig, `scroll: top down` oder `scroll: bottom up`, vertikales Scrolling startet und endet mit zufälligem Offset ≤ `kenburns_portrait_border_pct`
        - Wenn `kenburns_scroll_direction: up, down` für jedes Bild gleich, entsprechend `scroll: down = top down` oder `scroll: up = bottom up`, vertikales Scrolling startet und endet mit zufälligem Offset ≤ `kenburns_portrait_border_pct`

## scripts/pir_manager.py
- Steuert Slideshow und Display basierend auf Bewegungserkennung und Zeitplan.
- **Neu:** Wenn während der Nachtschaltung eine Bewegung erkannt wird, wird der Picframe-Dienst sofort gestartet und die Nachtschaltung für den Rest des Zyklus ausgesetzt.
- **Korrekturen & Änderungen:**
  - `HOLD`-Zustand über HTTP-Aufruf an den picframe-Webserver (ohne MQTT-Broker).  
  - `BLACK`-Zustand schaltet Bildschirm über `cec-client` ab.  
  - Display-Steuerung generell auf `cec-client` (statt `kmsblank`).  
  - HTTP-Port wird aus `configuration.yaml` gelesen.  
  - Timer-Fehler durch NTP-Zeitsprünge behoben (`time.monotonic()` statt `time.time()`).  
  - Stabilerer Start durch Wiederholungslogik beim HTTP-Aufruf.  
  - Pfadauflösung für Konfigurationsdatei korrigiert (`os.path.expanduser`).
- **Logik:**
  - Prüft alle 15 Minuten den PIR-Sensor.  
  - `HOLD`: Pausiert Slideshow nach 30 Minuten ohne Bewegung.  
  - `BLACK`: Bildschirm aus nach 1 Stunde ohne Bewegung.  
  - `OFF`: Nachtschaltung (00:00–07:00), beendet Dienst und schaltet Display ab (kann durch Bewegung unterbrochen werden).  
  - Startet Dienst und Display bei Bewegung oder am Morgen automatisch.

## picframe_scripts/sync_photos.sh
- Synchronisiert Fotos von einer SMB-Freigabe in den lokalen Cache (`picframe_cache`).
- **Ablauf:**
  - Wird stündlich per Cron ausgeführt.  
  - Prüft Erreichbarkeit des Servers (`sync_config.yaml`).  
  - Löscht leere Verzeichnisse.  
  - `filter_root_folders`: Filtert Stammordner via Regex (z. B. nur Jahreszahlen).  
  - Lädt zufällige Alben herunter, die noch nicht in `shown_albums.log` stehen.  
  - `maxPicsPerAlbum`: Beschränkt Fotos pro Album (nur jede n-te Datei).  
  - Löscht gezeigte Alben nach Eintrag in `shown_albums.log`.

## picframe_scripts/sync_config.yaml
- Neue Option `filter_root_folders`.  
- Umbenennung:  
  - `shuffle_Folder_Root` → `shuffle_folder_root`  
  - `shuffle_Album_Subfolder` → `shuffle_album_subfolder`

## picframe_scripts/watcher.sh
- Wrapper-Dienst, der `picframe` nach Systemstart im Hintergrund startet und am Laufen hält.

## picframe_scripts/install.sh
- Installiert System- und Python-Abhängigkeiten.
- **Ergänzungen:**  
  - `cec-utils` und `edid-decode` zu Systemabhängigkeiten hinzugefügt.  
  - Einrichtung von `systemd`-Diensten für `picframe.service` (via watcher) und `pir_manager.service`.  
  - Anweisungen für Cron-Job zur Foto-Synchronisation.

## picframe_scripts/test_pir.py
- Testskript für die Zustände (`ON`, `HOLD`, `BLACK`, `OFF`) von `pir_manager.py`.
- **Funktionen:**
  - Steuert `picframe`-Dienst und Display via `systemctl` und `cec-client`.  
  - Simuliert `HOLD` über HTTP-Aufruf.  
  - Wartet zwischen Zuständen 10 Sekunden.  
  - Liest nach der Testsequenz kontinuierlich den PIR-Sensor aus.

## src/picframe/image_cache.py
- SQLite-Datenbank als Cache für Bild-Metadaten (schnelleres Einlesen).
- Läuft in eigenem Thread, scannt Dateisystem periodisch.  
- Bietet Abfrage- und Löschmethoden für `model.py`-Funktionen (`group_by_dir`, `delete_after_show`).  
- **Korrektur:** Fehler beim Löschen von Datenbankeinträgen in der Klasse behoben.

## scripts/check_pic_dates.sh
- **Neu:** Shell-Skript zur Überprüfung und Korrektur von Bilddatumsangaben.
- **Funktionen:**
  - Iteriert durch Verzeichnisse mit Jahresnamen (z.B. `2023`).
  - Vergleicht das Verzeichnisjahr mit dem Erstellungs-, Änderungs- und EXIF-Datum von Bildern.
  - **EXIF-Daten vorhanden:**
    - Passt das Dateidatum an das EXIF-Datum an.
    - Fragt den Benutzer, ob die Datei in ein zum EXIF-Jahr passendes Verzeichnis verschoben werden soll.
  - **Keine EXIF-Daten vorhanden:**
    - Passt das Jahr des Dateidatums an das Verzeichnisjahr an.
  - Protokolliert alle Aktionen in einer Log-Datei (`check_pic_dates.log`).
- **DONE:** Extended file support to include video formats (mkv, mp4, mov, avi).
- **DONE:** Implemented metadata extraction for video files to read their creation date.

### scripts/sync_photos.sh
- **DONE:** Implement separate storage quotas for photos and videos.
- **DONE:** Use a single, unified cache directory for all media to ensure compatibility with picframe.
- **DONE:** Prioritize photo synchronization over video synchronization based on quota usage.
- **DONE:** Calculate media-specific storage usage to enforce quotas.
- **DONE:** Ensure `shown_albums.log` works for both photo and video albums by using a unified cache.
- **DONE:** Remove all automatic cache and log file cleanup logic.

### scripts/sync_config.yaml
- **DONE:** Restructure configuration for a unified cache and separate media quotas.

## scripts/create_test_images.sh
- **Neu:** Shell-Skript zur Erstellung von Testbildern für die Diashow.
- **Funktionen:**
  - Konvertiert alle PNG-Dateien im aktuellen Verzeichnis in das JPG-Format.
  - Liest Metadaten (Breite, Höhe, Farbraum, Bittiefe) aus den PNG-Dateien mittels `mediainfo`.
  - Brennt diese Metadaten als Text-Overlay direkt in das JPG-Bild ein. Die Position und Größe des Textes wird für Hoch- und Querformatbilder optimiert.
  - Fügt jedem JPG-Bild zufällige, aber realistische EXIF-Daten hinzu, einschließlich Geokoordinaten von bekannten Hauptstädten, um eine vielfältige Testdatenbank zu simulieren.

- viewer_display.py:
  - Added play_video_blocking to manage the entire video playback lifecycle.
  - Added _show_black_screen and _play_video_subprocess helper methods.
- viewer_process.py:
  - New file to display a single image and then exit.
- controller.py:
  - Simplified the main loop, delegating video playback to viewer_display.
- video_player.py:
  - Switched from python-vlc to a direct subprocess call to cvlc.
- video_streamer.py:
  - Adapted to manage the video_player.py script as a separate process.
- test/test_image_video_player.py:
  - Implemented screen blanking using 'dd' to hide console transitions.
- test/test_show_image.py:
  - New script to facilitate testing of single image display.
- test/test_video_player.py:
  - Updated tests to match the new subprocess-based video playback architecture.

## Done

- [x] **Implement robust video playback:**
    - [x] Integrate `mpv` as a stable external video player.
    - [x] Finalize the restart-after-video mechanism using a `watcher.sh` script and a special exit code.
    - [x] Abandoned the unstable in-process `pi3d` re-initialization approach.

- [x] **Implement seamless album resume logic:**
    - [x] Use `shown_albums.log` to track both completed albums and the next file to resume from.
    - [x] Ensure `picframe` continues at the correct file within an album after a video-induced restart.
    - [x] Fix the endless loop issue where only the first two files of an album were played.

- [x] **Improve Cache Stability:**
    - [x] Add error handling for video metadata extraction to prevent crashes.
    - [x] Fix all related `NameError`, `AttributeError`, and `IndentationError` bugs in the cache and model logic.

- [x] **Consolidate Installation:**
    - [x] Update `install.sh` to include all necessary system and Python dependencies.
    - [x] Create a `requirements.txt` for clear dependency management.

### Wie test_video_player.py funktioniert

1.  **Argumente parsen:** Das Skript nimmt Ihre gewünschten Parameter `--sec-per-frame` und `--blend-ratio` entgegen.
2.  **Videos finden:** Es durchsucht das Verzeichnis `test/videos` nach allen gängigen Videodateien.
3.  **`ffmpeg` als Generator:** Die Funktion `extract_frames` startet für jedes Video einen `ffmpeg`-Prozess im Hintergrund. Der Clou ist die Option `-f image2pipe`, die `ffmpeg` anweist, die extrahierten Frames nicht auf die Festplatte zu schreiben, sondern direkt in einen Datenstrom (`stdout`), den unser Python-Skript lesen kann. Dies ist sehr speicherschonend und vermeidet unnötige Schreib-/Lesezugriffe auf die SD-Karte.
4.  **`pi3d` Setup:** Es werden ein Display und zwei `pi3d.Sprite`-Objekte erstellt. Wir brauchen zwei, um einen weichen Übergang zu ermöglichen: `back_slide` (das aktuell sichtbare Bild) und `front_slide` (das nächste Bild, das eingeblendet wird). Beide nutzen den `blend_new`-Shader, den Sie bereits aus `picframe` kennen.
5.  **Die Hauptschleife:**
   *   Das Skript liest einen Frame aus dem `ffmpeg`-Datenstrom.
   *   Die Rohdaten werden mit `io.BytesIO` und `PIL.Image.open` zu einem Bildobjekt im Speicher verarbeitet.
   *   Daraus wird eine `pi3d.Texture` erstellt.
   *   Diese neue Textur wird dem `front_slide` zugewiesen.
   *   In einer kleinen Schleife wird der Alpha-Wert (Durchsichtigkeit) des `front_slide` über die berechnete `blend_time` von 0.0 auf 1.0 animiert. `pi3d` zeichnet dabei kontinuierlich beide Sprites, und der Shader erledigt die Magie des Überblendens.
   *   Nach der Überblendung wird die `hold_time` abgewartet, in der nur das neue Bild sichtbar ist.
   *   Anschließend werden die Rollen der Sprites getauscht (`front_slide` wird zu `back_slide`), und der Prozess beginnt für den nächsten Frame von vorn.

### Voraussetzungen und Ausführung

1.  **`ffmpeg` installieren:** Stellen Sie sicher, dass `ffmpeg` auf Ihrem Pi installiert ist:
   ```bash
   sudo apt-get update
   sudo apt-get install ffmpeg
   ```
2.  **Testvideos:** Legen Sie eine oder mehrere Videodateien in das Verzeichnis `picframe/test/videos`.
3.  **Skript ausführen:**
   Navigieren Sie in Ihr `picframe`-Verzeichnis und führen Sie das Skript mit den gewünschten Parametern aus. Zum Beispiel mit Ihren Werten:
   ```bash
   cd /home/schmali/picframe
   venv/bin/python test/test_video_slide_show.py --sec-per-frame 10 --blend-ratio 0.1
   ```
   Dies extrahiert alle 10 Sekunden einen Frame und verwendet 1 Sekunde (`10s * 0.1`) für die Überblendung.
