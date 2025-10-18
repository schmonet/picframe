#!/bin/bash

# This script checks and corrects the dates of media files (images and videos) in an archive.
# It compares the year from the directory name with the file's creation and
# modification dates, and with the metadata of the file (EXIF for images, container data for videos).

# Usage: ./check_pic_dates.sh /path/to/media/archive

# --- CONFIGURATION ---
LOG_FILE="check_pic_dates.log"
# List of file extensions to check, separated by |
FILE_EXTENSIONS="jpg|jpeg|png|heic|mkv|mp4|mov|avi"


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

PROCESS_ALL=false

# Find all year directories
for YEAR_DIR in */;
 do
    # Check if it is a directory and if the name is a four-digit number
    if [ -d "$YEAR_DIR" ] && [[ ${YEAR_DIR%/} =~ ^[0-9]{4}$ ]]; then
        YEAR_FROM_DIR=${YEAR_DIR%/}
        echo "Processing directory: $YEAR_DIR"

        if [ "$PROCESS_ALL" = false ]; then
            read -p "Continue? (Y/N/S/A) " -n 1 -r
            echo
        else
            REPLY="Y"
        fi

        case $REPLY in
            [Aa]* )
                PROCESS_ALL=true
                ;&
            [Yy]* )
                # Find all media files in the year directory
                find "$YEAR_DIR" -type f -iregex ".*\.(${FILE_EXTENSIONS})" -print0 | while IFS= read -r -d $'\0' FILE;
                 do
                    # Get the file creation and modification dates
                    CREATE_DATE=$(stat -c %y "$FILE")
                    MODIFY_DATE=$(stat -c %Y "$FILE")

                    # Get the year from the file dates
                    YEAR_FROM_CREATE=$(date -d "$CREATE_DATE" +%Y)
                    YEAR_FROM_MODIFY=$(date -d "@$MODIFY_DATE" +%Y)

                    # --- Metadata Extraction ---
                    # Try to get image EXIF date first, then fall back to common video date tags
                    META_DATE=$(exiftool -s -s -s -DateTimeOriginal "$FILE")
                    if [ -z "$META_DATE" ]; then
                        META_DATE=$(exiftool -s -s -s -CreateDate "$FILE")
                    fi
                    if [ -z "$META_DATE" ]; then
                        META_DATE=$(exiftool -s -s -s -MediaCreateDate "$FILE")
                    fi

                    if [ -n "$META_DATE" ] && [ "$META_DATE" != "0000:00:00 00:00:00" ]; then
                        # Normalize date format for reliable parsing
                        NORMALIZED_DATE=$(echo "$META_DATE" | sed 's/:/-/g')
                        YEAR_FROM_META=$(date -d "$NORMALIZED_DATE" +%Y 2>/dev/null || echo "")

                        if [ -z "$YEAR_FROM_META" ]; then
                            log_msg "Could not parse metadata date '$META_DATE' for file $FILE. Skipping metadata checks."
                            # Fall through to the 'no metadata' logic below
                        else
                            # 5.a - Update file date to match metadata date
                            if [ "$YEAR_FROM_META" != "$YEAR_FROM_CREATE" ] || [ "$YEAR_FROM_META" != "$YEAR_FROM_MODIFY" ]; then
                                FULL_META_DATE_FOR_TOUCH=$(date -d "$NORMALIZED_DATE" +%Y-%m-%dT%H:%M:%S)
                                log_msg "Updating file date for $FILE to metadata date $FULL_META_DATE_FOR_TOUCH"
                                touch -d "$FULL_META_DATE_FOR_TOUCH" "$FILE"
                            fi

                            # 5.b - Check if file needs to be moved to a different year directory
                            if [ "$YEAR_FROM_META" != "$YEAR_FROM_DIR" ]; then
                                read -p "Move $FILE to $ROOT_DIR/$YEAR_FROM_META? (Y/N) " -n 1 -r
                                echo
                                if [[ $REPLY =~ ^[Yy]$ ]]; then
                                    NEW_DIR="$ROOT_DIR/$YEAR_FROM_META/$(dirname "${FILE#*/}")"
                                    mkdir -p "$NEW_DIR"
                                    mv "$FILE" "$NEW_DIR"
                                    log_msg "Moved $FILE to $NEW_DIR"
                                fi
                            fi
                            continue # Skip to next file after handling metadata
                        fi
                    fi
                    
                    # 6.a - Logic for files with NO valid metadata
                    if [ "$YEAR_FROM_DIR" != "$YEAR_FROM_CREATE" ] || [ "$YEAR_FROM_DIR" != "$YEAR_FROM_MODIFY" ]; then
                        log_msg "No metadata found. Updating file year for $FILE to $YEAR_FROM_DIR"
                        MONTH_DAY_CREATE=$(date -d "$CREATE_DATE" +%m%d)
                        touch -t "${YEAR_FROM_DIR}${MONTH_DAY_CREATE}0000" "$FILE"
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
                if [ "$PROCESS_ALL" = false ]; then
                    echo "Invalid input. Aborting."
                    exit 1
                fi
                ;;
        esac
    fi
done