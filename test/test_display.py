"""
Minimales Test-Skript zur systematischen Fehlersuche beim pi3d-Start.

Anleitung:
1. Führen Sie dieses Skript auf dem Raspberry Pi aus:
   /home/schmali/picframe/venv/bin/python /home/schmali/picframe/test_display.py

2. Wenn es erfolgreich durchläuft, kommentieren Sie die nächste "TEST"-Zeile aus
   und wiederholen Sie den Vorgang.

3. Fahren Sie fort, bis das Skript mit dem bekannten Fehler
   "Failed to create pi3d display" abstürzt. Der zuletzt hinzugefügte Import
   ist die Ursache des Problems.
"""
import sys
import logging

# --- GRUNDLEGENDE IMPORTE ---
import time
import os

# --- PICFRAME-IMPORTE (schrittweise aktivieren) ---
# from picframe import default_config      # TEST 1: Nur Konfiguration
# from picframe import get_image_meta      # TEST 2: Metadaten-Helfer
# from picframe import mat_image           # TEST 3: Passepartout-Logik
# from picframe import controller          # TEST 4: Controller-Logik
# from picframe import viewer_display      # TEST 5: Die Viewer-Klasse selbst
# from picframe import model               # TEST 6: Das Model mit Threading


def main():
    logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')
    try:
        import pi3d
        logging.info("Versuche, pi3d.Display zu erstellen...")
        display = pi3d.Display.create(use_sdl2=False, layer=0) # layer=0 is crucial for headless Bookworm
        logging.info("pi3d.Display erfolgreich erstellt.")
        display.destroy()
        logging.info("pi3d.Display erfolgreich zerstört. Test bestanden.")
        sys.exit(0)
    except Exception as e:
        logging.critical("Fehler beim Erstellen des pi3d.Display:", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()