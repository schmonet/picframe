#!/bin/bash

# This script checks and corrects the dates of media files (images and videos) in an archive.
# It compares the year from the directory name with the file's creation and
# modification dates, and with the metadata of the file (EXIF for images, container data for videos).
#
# Rationale: photos copied between drives/cloud services over the years often lose their
# original filesystem timestamps, and scanned slides/negatives never had EXIF data to begin
# with. The one thing that usually stays reliable is the year folder they were manually sorted
# into. So the priority order used below is:
#   1. Trust real capture-time metadata (EXIF DateTimeOriginal/CreateDate, or video container
#      creation date) when present - it's the most accurate source.
#   2. If no metadata exists, fall back to the year encoded in the folder name (the manual
#      sorting), and stamp the file's timestamp to match it.
# The corrected timestamp is what picframe (via ImageCache) ultimately uses to sort/display
# images meaningfully when EXIF is absent.
#
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

# exiftool is required for the metadata lookups below; fail early with a clear message
# instead of silently treating every file as "no metadata found".
if ! command -v exiftool >/dev/null 2>&1; then
    echo "Error: exiftool is required but not found in PATH. Install it (e.g. 'apt install libimage-exiftool-perl')."
    exit 1
fi

# Set the root directory
ROOT_DIR="$1"

# Check if the root directory exists
if [ ! -d "$ROOT_DIR" ]; then
    echo "Directory not found: $ROOT_DIR"
    exit 1
fi

# Change to the root directory. Note: LOG_FILE is a relative path, so from here on it
# resolves inside ROOT_DIR (the log lives with the archive being processed, not next to
# the script).
cd "$ROOT_DIR" || exit

PROCESS_ALL=false

# Iterate over top-level year directories only (e.g. "2020/", "1998/") - anything not
# matching a plain 4-digit name (e.g. "mixed/", ".fullmix/") is skipped entirely.
for YEAR_DIR in */;
 do
    # Check if it is a directory and if the name is a four-digit number
    if [ -d "$YEAR_DIR" ] && [[ ${YEAR_DIR%/} =~ ^[0-9]{4}$ ]]; then
        YEAR_FROM_DIR=${YEAR_DIR%/}
        echo "Processing directory: $YEAR_DIR"

        # Per-directory prompt: Yes / No (abort) / Skip this dir / All (stop asking).
        if [ "$PROCESS_ALL" = false ]; then
            read -p "Continue? (Y/N/S/A) " -n 1 -r
            echo
        else
            REPLY="Y"
        fi

        case $REPLY in
            [Aa]* )
                PROCESS_ALL=true
                ;&  # fall through into the Y branch below - "All" implies processing this dir too
            [Yy]* )
                # Find all media files in the year directory, NUL-delimited so filenames
                # with spaces/newlines are handled safely.
                find "$YEAR_DIR" -type f -iregex ".*\.(${FILE_EXTENSIONS})" -print0 | while IFS= read -r -d $'\0' FILE;
                 do
                    # --- Filesystem timestamps ---
                    # Prefer the filesystem's true "birth time" (%w) if the OS/filesystem
                    # exposes it (e.g. ext4 with a recent kernel+stat). Most Linux setups
                    # historically don't track this, in which case stat prints "-" and we
                    # fall back to the last-modified time (%y) instead - which is NOT the
                    # same thing as a creation date, just the best available substitute.
                    CREATE_DATE=$(stat -c %w "$FILE")
                    if [ "$CREATE_DATE" = "-" ] || [ -z "$CREATE_DATE" ]; then
                        CREATE_DATE=$(stat -c %y "$FILE")
                    fi
                    MODIFY_DATE=$(stat -c %Y "$FILE")

                    # Get the year from the file dates
                    YEAR_FROM_CREATE=$(date -d "$CREATE_DATE" +%Y)
                    YEAR_FROM_MODIFY=$(date -d "@$MODIFY_DATE" +%Y)

                    # --- Metadata Extraction ---
                    # Try to get image EXIF date first, then fall back to common video date tags.
                    # This is the authoritative source when present - takes priority over both
                    # the filesystem timestamps above and the year folder name.
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
                            # 5.a - Filesystem timestamp doesn't match EXIF: re-stamp the file
                            # to the real capture date so picframe/file managers sort correctly.
                            if [ "$YEAR_FROM_META" != "$YEAR_FROM_CREATE" ] || [ "$YEAR_FROM_META" != "$YEAR_FROM_MODIFY" ]; then
                                FULL_META_DATE_FOR_TOUCH=$(date -d "$NORMALIZED_DATE" +%Y-%m-%dT%H:%M:%S)
                                log_msg "Updating file date for $FILE to metadata date $FULL_META_DATE_FOR_TOUCH"
                                touch -d "$FULL_META_DATE_FOR_TOUCH" "$FILE"
                            fi

                            # 5.b - EXIF year disagrees with the folder it's filed under:
                            # offer to move it into the correct year folder (interactive,
                            # per file). Reads from the real terminal (/dev/tty) rather than
                            # stdin, because stdin here is connected to the `find` pipe feeding
                            # this while-loop, not the keyboard - without this redirect the
                            # prompt would silently read piped data instead of user input.
                            if [ "$YEAR_FROM_META" != "$YEAR_FROM_DIR" ]; then
                                read -p "Move $FILE to $ROOT_DIR/$YEAR_FROM_META? (Y/N) " -n 1 -r < /dev/tty
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

                    # 6.a - No usable metadata at all: trust the manual year-folder sorting
                    # instead (this is the deliberate fallback for slide/negative scans etc.
                    # that never had EXIF, mentioned in the script's header comment). Keeps the
                    # original month/day, only corrects the year to match the folder.
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
