#!/bin/bash
#
# create_test_images.sh
#
# Converts all PNG files in the current directory to JPG, burns image metadata
# onto the image, and adds randomized EXIF data including GPS coordinates.
#
# Dependencies:
# - imagemagick: for image conversion and text overlay.
# - mediainfo: for reading image metadata.
# - exiftool (libimage-exiftool-perl): for writing EXIF data.
#
# To install on Ubuntu/Debian:
# sudo apt-get update
# sudo apt-get install imagemagick mediainfo libimage-exiftool-perl
#

# --- Dependency Check ---
for cmd in convert mediainfo exiftool; do
  if ! command -v "$cmd" &> /dev/null; then
    echo "Fehler: Das benötigte Kommando '$cmd' wurde nicht gefunden."
    echo "Bitte installieren Sie es. Auf Ubuntu/Debian: sudo apt-get install imagemagick mediainfo libimage-exiftool-perl"
    exit 1
  fi
done

# --- Data for Randomization ---

# Array of "City,Latitude,Longitude"
declare -a CAPITALS=(
  "Berlin,52.5200,13.4050"
  "Paris,48.8566,2.3522"
  "Madrid,40.4168,-3.7038"
  "Rom,41.9028,12.4964"
  "Washington D.C.,38.9072,-77.0369"
  "Tokio,35.6895,139.6917"
  "Canberra,-35.2809,149.1300"
  "Kairo,30.0444,31.2357"
  "Moskau,55.7558,37.6173"
  "Peking,39.9042,116.4074"
)

# Array of "Make,Model"
declare -a CAMERAS=(
  "SONY,ILCE-7M3"
  "Canon,Canon EOS R5"
  "NIKON CORPORATION,NIKON Z 7"
  "FUJIFILM,X-T4"
  "Apple,iPhone 14 Pro"
  "Google,Pixel 7 Pro"
)


# --- Main Loop ---

# Check if there are any PNG files to process
if ! ls *.png 1> /dev/null 2>&1; then
    echo "Keine PNG-Dateien im aktuellen Verzeichnis gefunden."
    exit 0
fi

for png_file in *.png; do
  jpg_file="${png_file%.png}.jpg"
  echo "Verarbeite '$png_file' -> '$jpg_file' நான"

  # 1. Convert PNG to JPG
  convert "$png_file" "$jpg_file"

  # 2. Extract metadata using MediaInfo
  echo "  - Lese Metadaten..."
  width_str=$(mediainfo "$png_file" | grep 'Width' | head -n1 | cut -d ':' -f 2 | xargs)
  height_str=$(mediainfo "$png_file" | grep 'Height' | head -n1 | cut -d ':' -f 2 | xargs)
  dar=$(mediainfo "$png_file" | grep 'Display aspect ratio' | head -n1 | cut -d ':' -f 2 | xargs)
  cspace=$(mediainfo "$png_file" | grep 'Color space' | head -n1 | cut -d ':' -f 2 | xargs)
  bdepth=$(mediainfo "$png_file" | grep 'Bit depth' | head -n1 | cut -d ':' -f 2 | xargs)

  # Prepare text for overlay
  info_text="Width: $width_str\nHeight: $height_str\nAspect Ratio: $dar\nColor Space: $cspace\nBit Depth: $bdepth"

  # 3. Burn text onto the JPG image
  echo "  - Schreibe Metadaten auf das Bild..."

  # Get numeric dimensions to check orientation
  img_width_num=$(echo "$width_str" | tr -dc '0-9')
  img_height_num=$(echo "$height_str" | tr -dc '0-9')

  # Default settings for landscape/square
  pointsize=24
  y_offset=$(( - (img_height_num * 15) / 100 )) # 15% upward offset

  # Overwrite for portrait images
  if [ "$img_height_num" -gt "$img_width_num" ]; then
    echo "  - Hochformat erkannt. Passe Text an."
    pointsize=28 # ~15% larger
    y_offset=$(( - (img_height_num * 8) / 100 )) # 8% upward offset (moved down by 7%)
  fi

  # Using a bold font makes letters thicker and the 1px stroke appear relatively thinner.
  # DejaVu-Sans-Bold is a common font on Linux systems.
  convert "$jpg_file" \
    -font DejaVu-Sans-Bold \
    -pointsize "$pointsize" \
    -gravity center \
    -fill white \
    -stroke black -strokewidth 1 \
    -annotate +0${y_offset} "$info_text" \
    "$jpg_file"

  # 4. Add random EXIF data
  echo "  - Füge zufällige EXIF-Daten hinzu..."

  # Random date within the last 10 years
  random_seconds=$((RANDOM * RANDOM % (3600*24*365*10)))
  random_date=$(date -d "now - $random_seconds seconds" "+%Y:%m:%d %H:%M:%S")

  # Random camera
  random_camera_data=${CAMERAS[$RANDOM % ${#CAMERAS[@]}]}
  IFS=',' read -r make model <<< "$random_camera_data"

  # Random camera settings
  # Calculate f-number and manually replace comma with period to avoid locale issues.
  f_number_raw=$(echo "scale=1; 1.8 + $RANDOM / 32767 * 10" | bc)
  f_number=${f_number_raw/,/.} # Replace first comma with a period
  iso=$((100 * (1 + RANDOM % 32))) # 100 to 3200 in steps of 100
  exposure_time="1/$((50 + RANDOM % 451))" # 1/50 to 1/500

  # Random GPS from capitals list
  random_capital_data=${CAPITALS[$RANDOM % ${#CAPITALS[@]}]}
  IFS=',' read -r city lat lon <<< "$random_capital_data"

  lat_ref="N"
  lon_ref="E"
  # Handle southern and western hemispheres
  if (( $(echo "$lat < 0" | bc -l) )); then
    lat_ref="S"
    lat=$(echo "$lat * -1" | bc -l)
  fi
  if (( $(echo "$lon < 0" | bc -l) )); then
    lon_ref="W"
    lon=$(echo "$lon * -1" | bc -l)
  fi

  # Use exiftool to write all tags at once
  exiftool -overwrite_original -q \
    -Make="$make" \
    -Model="$model" \
    -DateTimeOriginal="$random_date" \
    -CreateDate="$random_date" \
    -FNumber="$f_number" \
    -ISO="$iso" \
    -ExposureTime="$exposure_time" \
    -GPSLatitude="$lat" \
    -GPSLatitudeRef="$lat_ref" \
    -GPSLongitude="$lon" \
    -GPSLongitudeRef="$lon_ref" \
    -City="$city" \
    "$jpg_file"
done

echo -e "\nFertig! Alle PNG-Dateien wurden erfolgreich verarbeitet."
