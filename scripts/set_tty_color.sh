#!/bin/bash

# --- Ubuntu TTY Color Fix Installer ---

# Sicherheitsprüfung: Skript nur als root ausführen
if [ "$EUID" -ne 0 ]; then
  echo "❌ Dieses Skript muss mit sudo oder als root ausgeführt werden."
  exit 1
fi

# 1. Definiere den Inhalt des Systemd Service
SERVICE_NAME="tty-color-fix.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

SERVICE_CONTENT="[Unit]
Description=Forcibly set console background color after TTY init
After=getty.target
Wants=getty.target

[Service]
Type=oneshot
# Befehl: 1. Warten. 2. Farben setzen (weiß/grau). 3. Aggressives Scrollen (50 Zeilen)
ExecStart=/bin/sh -c '/bin/sleep 2 && /usr/bin/setterm -term linux -back white -fore white -clear > /dev/tty1 && /bin/echo -e \"\n%.0s\" {1..50} > /dev/tty1'

[Install]
WantedBy=multi-user.target
"

echo "🛠️ Erstelle den Systemd-Dienst: $SERVICE_NAME..."

# 2. Schreibe den Service-Inhalt in die Datei
echo "$SERVICE_CONTENT" > "$SERVICE_PATH"

if [ $? -eq 0 ]; then
    echo "✅ Dienstdatei erfolgreich erstellt."
else
    echo "❌ Fehler beim Erstellen der Dienstdatei."
    exit 1
fi

# 3. Systemd neu laden, Dienst aktivieren und starten
echo "⚙️ Lade Systemd neu und aktiviere den Dienst..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

if [ $? -eq 0 ]; then
    echo "✅ Dienst aktiviert und gestartet."
else
    echo "❌ Fehler beim Aktivieren/Starten des Dienstes."
    exit 1
fi

echo "---"
echo "🎉 Installation abgeschlossen."
echo "⚠️ Das System muss neu gestartet werden, um die Änderung dauerhaft anzuwenden."
read -r -p "Möchten Sie jetzt neu starten? (j/n): " REBOOT_CHOICE

if [[ "$REBOOT_CHOICE" =~ ^[Jj]$ ]]; then
    echo "⬇️ System wird neu gestartet..."
    reboot
else
    echo "Bitte starten Sie das System manuell neu, um die TTY-Farbkorrektur zu aktivieren."
fi

exit 0