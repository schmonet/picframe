#!/bin/bash

# This script checks and corrects the dates of image files in a photo archive.
# It compares the year from the directory name with the file's creation and
# modification dates, and with the EXIF data of the image.

# Usage: ./check_pic_dates.sh /path/to/photo/archive

# --- CONFIGURATION ---
LOG_FILE="check_pic_dates.log"


# --- FUNCTIONS ---

# Log a message to the console and to the log file
log_msg() {
    echo "$(date +'%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# --- SCRIPT ---

# Check if a directory was provided
if [ -z "$1" ]; then
    echo "Usage: $0 <directory>"
    exit 1
fi

# Set the root directory
ROOT_DIR="$1"

# Check if the root directory exists
if [ ! -d "$ROOT_DIR" ]; then
    echo "Directory not found: $ROOT_DIR"
    exit 1
fi

# Change to the root directory
cd "$ROOT_DIR" || exit

# Find all year directories
for YEAR_DIR in */;
 do
    # Check if it is a directory and if the name is a four-digit number
    if [ -d "$YEAR_DIR" ] && [[ ${YEAR_DIR%/} =~ ^[0-9]{4}$ ]]; then
        YEAR_FROM_DIR=${YEAR_DIR%/}
        echo "Processing directory: $YEAR_DIR"
        read -p "Continue? (Y/N/S) " -n 1 -r
        echo
        case $REPLY in
            [Yy]* )
                # Find all image files in the year directory
                find "$YEAR_DIR" -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) -print0 | while IFS= read -r -d $'' FILE;
                 do
                    # Get the file creation and modification dates
                    CREATE_DATE=$(stat -c %y "$FILE")
                    MODIFY_DATE=$(stat -c %Y "$FILE")

                    # Get the year from the file dates
                    YEAR_FROM_CREATE=$(date -d "$CREATE_DATE" +%Y)
                    YEAR_FROM_MODIFY=$(date -d "@$MODIFY_DATE" +%Y)

                    # Get the EXIF date
                    EXIF_DATE=$(exiftool -s -s -s -DateTimeOriginal "$FILE")

                    if [ -n "$EXIF_DATE" ]; then
                        YEAR_FROM_EXIF=$(echo "$EXIF_DATE" | cut -d: -f1)

                        # 5.a
                        if [ "$YEAR_FROM_EXIF" != "$YEAR_FROM_CREATE" ] || [ "$YEAR_FROM_EXIF" != "$YEAR_FROM_MODIFY" ]; then
                            log_msg "Updating file date for $FILE to EXIF date $EXIF_DATE"
                            touch -d "$EXIF_DATE" "$FILE"
                        fi

                        # 5.b
                        if [ "$YEAR_FROM_EXIF" != "$YEAR_FROM_DIR" ]; then
                            read -p "Move $FILE to $ROOT_DIR/$YEAR_FROM_EXIF? (Y/N) " -n 1 -r
                            echo
                            if [[ $REPLY =~ ^[Yy]$ ]]; then
                                NEW_DIR="$ROOT_DIR/$YEAR_FROM_EXIF/$(dirname "${FILE#*/}")"
                                mkdir -p "$NEW_DIR"
                                mv "$FILE" "$NEW_DIR"
                                log_msg "Moved $FILE to $NEW_DIR"
                            fi
                        fi
                    else
                        # 6.a
                        if [ "$YEAR_FROM_DIR" != "$YEAR_FROM_CREATE" ] || [ "$YEAR_FROM_DIR" != "$YEAR_FROM_MODIFY" ]; then
                            log_msg "Updating year for $FILE to $YEAR_FROM_DIR"
                            MONTH_DAY_CREATE=$(date -d "$CREATE_DATE" +%m%d)
                            touch -t "${YEAR_FROM_DIR}${MONTH_DAY_CREATE}0000" "$FILE"
                        fi
                    fi
                done
                ;;
            [Ss]* )
                echo "Skipping directory: $YEAR_DIR"
                ;;
            [Nn]* )
                echo "Aborting."
                exit 0
                ;;
            * )
                echo "Invalid input. Aborting."
                exit 1
                ;;
        esac
    fi
done
