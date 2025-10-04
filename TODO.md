# Funktionsbeschreibung der geänderten und hinzugefügten Dateien

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

## picframe_scripts/pir_manager.py
- Steuert Slideshow und Display basierend auf Bewegungserkennung und Zeitplan.
- **Korrekturen & Änderungen:**
  - `HOLD`-Zustand über HTTP-Aufruf an den picframe-Webserver (ohne MQTT-Broker).  
  - `BLACK`-Zustand schaltet Bildschirm über `cec-client` ab.  
  - Display-Steuerung generell auf `cec-client` (statt `kmsblank`).  
  - HTTP-Port wird aus `configuration.yaml` gelesen.  
  - Timer-Fehler durch NTP-Zeitsprünge behoben (`time.monotonic()` statt `time.time()`).  
  - Stabilerer Start durch Wiederholungslogik beim HTTP-Aufruf.  
- **Logik:**
  - Prüft alle 15 Minuten den PIR-Sensor.  
  - `HOLD`: Pausiert Slideshow nach 30 Minuten ohne Bewegung.  
  - `BLACK`: Bildschirm aus nach 1 Stunde ohne Bewegung.  
  - `OFF`: Nachtschaltung (00:00–06:00), beendet Dienst und schaltet Display ab.  
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