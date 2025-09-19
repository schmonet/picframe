#!/bin/bash
set -e

log_msg() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') [Sync] $1"
}

USER_HOME="$HOME"
CONFIG_FILE="$USER_HOME/picframe/picframe_scripts/sync_config.yaml"
SHOWN_ALBUMS_LOG="$USER_HOME/shown_albums.log"
PICFRAME_CACHE_PATH="$USER_HOME/picframe_cache"
# Function to read a value from the YAML config file
get_config() {
    awk -F': *' '/^'$1':/{print $2}' "$CONFIG_FILE" | tr -d '"'
}
log_msg "Checking for shown albums to clean up..."
log_msg "Cleaning up empty directories in cache..."
find "$PICFRAME_CACHE_PATH" -mindepth 1 -type d -empty -delete

touch "$SHOWN_ALBUMS_LOG"
# Read the log of shown albums to delete them from the cache
mapfile -t albums_to_delete < <(cat "$SHOWN_ALBUMS_LOG")
if [ ${#albums_to_delete[@]} -gt 0 ]; then
    log_msg "Found ${#albums_to_delete[@]} album(s) in log to delete from cache."
    for album_path in "${albums_to_delete[@]}"; do
        if [ -d "$album_path" ]; then
            log_msg "Deleting $album_path..."
            rm -rf "$album_path"
        fi
    done
    
fi
# Read sync configuration
SERVER_IP=$(get_config "server_ip")
SHARE_NAME=$(get_config "share_name")
CREDENTIALS_FILE="$USER_HOME/.smb_credentials"
MOUNT_POINT=$(get_config "mount_point")
MAX_PICS_PER_ALBUM=$(get_config "max_pics_per_album")
MAX_CACHE_SIZE_GB=$(get_config "max_cache_size_gb")
SMB_VERSION=$(get_config "smb_version")
DOMAIN=$(get_config "domain")
log_msg "Starting photo sync process..."

# Check if server is online
if ! ping -c 1 -W 3 "$SERVER_IP" &> /dev/null; then
    log_msg "Server $SERVER_IP is not reachable. Exiting."
    exit 1
fi
# Check for credentials file
if [ ! -f "$CREDENTIALS_FILE" ]; then
    log_msg "Credentials file not found at $CREDENTIALS_FILE. Exiting."
    exit 1
fi
# Mount the network share
sudo mkdir -p "$MOUNT_POINT"
if ! mountpoint -q "$MOUNT_POINT"; then
    sudo mount -t cifs "//$SERVER_IP/$SHARE_NAME" "$MOUNT_POINT" -o "credentials=$CREDENTIALS_FILE,iocharset=utf8,vers=$SMB_VERSION,domain=$DOMAIN"
fi
# Unmount share on exit
trap 'sudo umount "$MOUNT_POINT" &>/dev/null || true' EXIT
# Main sync loop
while true; do
    # Check cache size
    current_cache_size_gb=$(echo "scale=2; $(du -sb "$PICFRAME_CACHE_PATH" | awk '{print $1}') / 1073741824" | bc)
    if (( $(echo "$current_cache_size_gb >= $MAX_CACHE_SIZE_GB" | bc -l) )); then
        log_msg "Cache is full ($current_cache_size_gb GB / $MAX_CACHE_SIZE_GB GB). Exiting loop."
        break
    fi
    # Select a random album from the source
    FILTER_ROOT_FOLDERS_RAW=$(get_config "filter_root_folders")
    if [ -n "$FILTER_ROOT_FOLDERS_RAW" ]; then
        log_msg "Using root folder filter: $FILTER_ROOT_FOLDERS_RAW"
        FILTER_ROOT_FOLDERS=$(echo "$FILTER_ROOT_FOLDERS_RAW" | sed 's,^/,,;s,/$,,')
        mapfile -t year_dirs < <(find "$MOUNT_POINT" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | grep -E "$FILTER_ROOT_FOLDERS")
    else
        mapfile -t year_dirs < <(find "$MOUNT_POINT" -maxdepth 1 -mindepth 1 -type d -printf '%f\n')
    fi
    if [ ${#year_dirs[@]} -eq 0 ]; then log_msg "No year directories found on share."; break; fi
    random_year=${year_dirs[$RANDOM % ${#year_dirs[@]}]}
    mapfile -t album_dirs < <(find "$MOUNT_POINT/$random_year" -maxdepth 1 -mindepth 1 -type d -printf '%f\n')
    if [ ${#album_dirs[@]} -eq 0 ]; then continue; fi
    random_album=${album_dirs[$RANDOM % ${#album_dirs[@]}]}
    DEST_ALBUM_PATH="$PICFRAME_CACHE_PATH/$random_year/$random_album"
    # Skip if album already exists in cache
    if [ -d "$DEST_ALBUM_PATH" ]; then continue; fi
    
    # Skip if album has been shown before (is in the log)
    if grep -q -x -F "$DEST_ALBUM_PATH" "$SHOWN_ALBUMS_LOG"; then
        log_msg "Skipping already shown album: $random_year/$random_album"
        continue
    fi

    SOURCE_ALBUM_PATH="$MOUNT_POINT/$random_year/$random_album"
    mapfile -t all_pics < <(find "$SOURCE_ALBUM_PATH" -type f -not -name '._*' -iregex '.*\.\(jpg\|jpeg\|png\|heic\)' | sort)
    num_pics=${#all_pics[@]}
    if [ $num_pics -eq 0 ]; then continue; fi

    TMP_DEST_ALBUM_PATH="$DEST_ALBUM_PATH.tmp"
    log_msg "Downloading album to temporary directory: $random_year/$random_album.tmp"
    mkdir -p "$TMP_DEST_ALBUM_PATH"

    # Copy a subset of pictures
    interval=1
    if [ "$num_pics" -gt "$MAX_PICS_PER_ALBUM" ]; then interval=$((num_pics / MAX_PICS_PER_ALBUM)); fi
    log_msg "Found $num_pics pictures. Copying every ${interval}-th picture."
    current_pic_index=0
    for ((i=0; i<num_pics; i+=interval)); do
        cp -p "${all_pics[$i]}" "$TMP_DEST_ALBUM_PATH/"
        if [ $((++current_pic_index)) -ge $MAX_PICS_PER_ALBUM ]; then break; fi
    done

    # Preserve the directory timestamp
    log_msg "Preserving timestamp for temporary directory"
    touch -r "$SOURCE_ALBUM_PATH" "$TMP_DEST_ALBUM_PATH"

    # Atomically move the directory
    log_msg "Finalizing album: $random_year/$random_album"
    mv "$TMP_DEST_ALBUM_PATH" "$DEST_ALBUM_PATH"
done
log_msg "Sync process finished."

