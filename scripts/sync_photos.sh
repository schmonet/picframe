#!/bin/bash

# ========================================================================================
#
# Media Synchronization Script for Picframe
#
# This script synchronizes photos and videos from remote SMB shares to a single, 
# unified local cache directory. It is designed to be run periodically (e.g., via cron).
#
# Key Features:
# - FILLS a unified cache, managing separate quotas for photos and videos.
# - Does NOT delete any existing files (manual cache management is assumed).
# - Prioritizes photo sync and only syncs videos if the photo quota is nearly full.
# - Randomly selects new albums to add to the cache.
#
# ========================================================================================

set -e

# --- CONFIGURATION ---
SCRIPT_DIR=$(dirname "$(realpath "$0")")
CONFIG_FILE="$SCRIPT_DIR/sync_config.yaml"
DEBUG=false

# --- HELPER FUNCTIONS ---

log_msg() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') [Sync] $1"
}

debug_msg() {
    if [ "$DEBUG" = "true" ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') [Sync] [DEBUG] $1"
    fi
}

# Function to read a value from the YAML config file.
# Usage: get_config <section> <key>
get_config() {
    local section=$1
    local key=$2
    # Use sed to parse the simple two-level YAML structure
    sed -n "/^$section:/,/^[^ ]/ { /^[[:space:]]*['\"]\{0,1\}$key['\"]\{0,1\}:/ { s/^[[:space:]]*['\"]\{0,1\}$key['\"]\{0,1\}:[[:space:]]*//; s/[[:space:]]*#.*$//; s/[[:space:]]*$//; s/^['\"]//; s/['\"]$//; p } }" "$CONFIG_FILE"
}

# Function to get the total size of files of a certain type in the cache
# Usage: get_media_size_gb <file_extension_pattern>
get_media_size_gb() {
    local pattern=$1
    local cache_path=$(eval echo "$(get_config "common" "cache_path")")
    
    if [ ! -d "$cache_path" ]; then
        echo "0.00"
        return
    fi

    # Find files, get their total size in bytes, and convert to GB
    # Use -r to prevent xargs from running du on current dir if no files found
    local total_bytes=$(find "$cache_path" -type f -regextype posix-extended -iregex ".*\.(${pattern})" -print0 | xargs -0 -r du -cb | tail -n1 | awk '{print $1}')
    
    if [ -z "$total_bytes" ]; then
        total_bytes=0
    fi
    echo "scale=2; $total_bytes / 1073741824" | bc
}

# --- CLEANUP TRAP ---

cleanup() {
    rm -f /dev/shm/picframe_download.flag
    local mount_point=$(get_config "common" "mount_point")
    if [ -n "$mount_point" ] && mountpoint -q "$mount_point"; then
        sudo umount -l "$mount_point" >/dev/null 2>&1
    fi
}
trap cleanup EXIT

# --- MAIN SYNC FUNCTION ---

# This function performs the synchronization for a given media type (photo or video).
# Usage: run_sync <photo|video>
run_sync() {
    local sync_type=$1
    log_msg "Starting sync process for: ${sync_type}s..."

    # --- Read Configuration for the given sync type ---
    local enabled=$(get_config "${sync_type}_sync" "enabled")
    if [ "$enabled" != "true" ]; then
        log_msg "Sync for ${sync_type}s is disabled in the config. Skipping."
        return
    fi

    local share_name=$(get_config "${sync_type}_sync" "share_name")
    local quota_gb=$(get_config "${sync_type}_sync" "quota_gb")
    local max_pics_per_album=$(get_config "${sync_type}_sync" "max_pics_per_album")
    local filter_root_folders_raw=$(get_config "${sync_type}_sync" "filter_root_folders")
    local file_extensions=$(get_config "${sync_type}_sync" "file_extensions")

    # --- Common Config ---
    local server_ip=$(get_config "common" "server_ip")
    local credentials_file=$(eval echo "$(get_config "common" "credentials_file")")
    local domain=$(get_config "common" "domain")
    local smb_version=$(get_config "common" "smb_version")
    local mount_point=$(get_config "common" "mount_point")
    local cache_path=$(eval echo "$(get_config "common" "cache_path")")
    local shown_albums_log=$(eval echo "$(get_config "common" "shown_albums_log")")
    
    # --- Safety Check for Disk Space ---
    # Ensure cache path exists for df
    mkdir -p "$cache_path"
    
    # Available space in 1K blocks
    local avail_k=$(df --output=avail "$cache_path" | tail -n1)
    # Convert to GB
    local avail_gb=$(echo "scale=2; $avail_k / 1024 / 1024" | bc)
    
    # Current usage of this media type
    local current_media_size_gb=$(get_media_size_gb "$file_extensions")
    
    # Max allowed size for this media type = Current Size + Available Space - 1GB Buffer
    local max_safe_gb=$(echo "scale=2; $current_media_size_gb + $avail_gb - 1.0" | bc)
    
    log_msg "Status: ${sync_type} usage: ${current_media_size_gb} GB (Quota: ${quota_gb} GB, Free: ${avail_gb} GB)"

    if (( $(echo "$quota_gb > $max_safe_gb" | bc -l) )); then
        log_msg "WARNING: Configured quota ($quota_gb GB) exceeds safe available space."
        log_msg "  Current Usage: $current_media_size_gb GB | Free Space: $avail_gb GB"
        log_msg "  Reducing quota to: $max_safe_gb GB (keeping 1GB free)"
        quota_gb=$max_safe_gb
    fi

    # --- Mount and Sync Logic ---
    if mountpoint -q "$mount_point"; then
        log_msg "Mount point $mount_point is already in use. Unmounting to ensure correct share..."
        sudo umount -l "$mount_point"
    fi
    
    # Recreate mount point to ensure clean state
    if [ -d "$mount_point" ]; then
        sudo rmdir "$mount_point" 2>/dev/null || true
    fi
    sudo mkdir -p "$mount_point"

    log_msg "Mounting $share_name..."
    
    # Capture mount output and exit code, with timeout to prevent hangs
    set +e
    MOUNT_OUTPUT=$(timeout 30s sudo mount -t cifs "//$server_ip/$share_name" "$mount_point" -o "credentials=$credentials_file,iocharset=utf8,vers=$smb_version,domain=$domain,uid=$(id -u),gid=$(id -g)" 2>&1)
    MOUNT_RET=$?
    set -e

    if [ $MOUNT_RET -ne 0 ]; then
        log_msg "CRITICAL: Mount failed (Ret=$MOUNT_RET). Output: $MOUNT_OUTPUT"
        exit 1
    fi
    log_msg "Mount successful."

    # Ensure cache path exists
    mkdir -p "$cache_path"
    touch "$shown_albums_log"

    # --- Sync Loop ---
    log_msg "Starting sync loop..."
    while true; do
        debug_msg "Checking media quota..."
        # Check media-specific quota
        local current_media_size_gb=$(get_media_size_gb "$file_extensions")
        if (( $(echo "$current_media_size_gb >= $quota_gb" | bc -l) )); then
            log_msg "${sync_type} quota is full ($current_media_size_gb GB / $quota_gb GB). Exiting loop."
            break
        fi

        debug_msg "Searching for year directories in $mount_point..."
        # Select a random album from the source (random selection is maintained)
        local filter_root_folders
        if [ -n "$filter_root_folders_raw" ]; then
            filter_root_folders=$(echo "$filter_root_folders_raw" | sed 's,^/,,;s,/$,,')
            mapfile -t year_dirs < <(timeout 30s find "$mount_point" -maxdepth 1 -mindepth 1 -type d -printf '%f\n' | grep -E "$filter_root_folders")
        else
            mapfile -t year_dirs < <(timeout 30s find "$mount_point" -maxdepth 1 -mindepth 1 -type d -printf '%f\n')
        fi

        debug_msg "Found ${#year_dirs[@]} year directories."

        if [ ${#year_dirs[@]} -eq 0 ]; then 
            log_msg "No year directories found on share '$share_name'."
            if [ "$DEBUG" = "true" ]; then
                debug_msg "Listing mount point content:"
                ls -la "$mount_point" | head -n 5
            fi
            break
        fi
        local random_year=${year_dirs[$RANDOM % ${#year_dirs[@]}]}
        debug_msg "Selected year: $random_year. Searching for albums..."
        
        mapfile -t album_dirs < <(timeout 30s find "$mount_point/$random_year" -maxdepth 1 -mindepth 1 -type d -printf '%f\n')
        
        debug_msg "Found ${#album_dirs[@]} albums in $random_year."
        
        if [ ${#album_dirs[@]} -eq 0 ]; then continue; fi
        local random_album=${album_dirs[$RANDOM % ${#album_dirs[@]}]}
        
        debug_msg "Selected album candidate: $random_album"
        
        local dest_album_path="$cache_path/$random_year/$random_album"
        
        # Skip if album already exists in cache
        if [ -d "$dest_album_path" ]; then 
            debug_msg "Album already exists in cache. Skipping."
            continue # Silently skip to find a new one faster
        fi
        # Skip if album has been marked as shown by picframe
        if grep -q -x -F "$dest_album_path" "$shown_albums_log"; then
            debug_msg "Album marked as shown. Skipping."
            continue # Silently skip
        fi

        debug_msg "Album accepted. Listing files..."
        local source_album_path="$mount_point/$random_year/$random_album"
        debug_msg "Executing find with regex: .*\.(${file_extensions})"
        mapfile -t all_media < <(timeout 60s find "$source_album_path" -type f -not -name '._*' -regextype posix-extended -iregex ".*\.(${file_extensions})" | sort)
        local num_media=${#all_media[@]}
        debug_msg "Found $num_media files in album."
        
        if [ $num_media -eq 0 ]; then continue; fi

        local tmp_dest_album_path="$dest_album_path.tmp"
        log_msg "Downloading album to temporary directory: $random_year/$random_album.tmp"
        mkdir -p "$tmp_dest_album_path"

        # Copy a subset of media files
        local interval=1
        if [ "$num_media" -gt "$max_pics_per_album" ]; then interval=$((num_media / max_pics_per_album)); fi
        log_msg "Found $num_media files. Copying every ${interval}-th file."
        local current_pic_index=0
        for ((i=0; i<num_media; i+=interval)); do
            cp -p "${all_media[$i]}" "$tmp_dest_album_path/"
            if [ $((++current_pic_index)) -ge $max_pics_per_album ]; then break; fi
        done

        touch -r "$source_album_path" "$tmp_dest_album_path"
        log_msg "Finalizing album: $random_year/$random_album"
        mv "$tmp_dest_album_path" "$dest_album_path"
    done

    # --- Unmount ---
    if mountpoint -q "$mount_point"; then
        log_msg "Unmounting $share_name..."
        sudo umount -l "$mount_point"
    fi
}

# --- SCRIPT EXECUTION ---

log_msg "Starting media sync process..."

# 1. Check for server connectivity before doing anything
SERVER_IP=$(get_config "common" "server_ip")
if ! ping -c 1 -W 3 "$SERVER_IP" &> /dev/null; then
    log_msg "Server $SERVER_IP is not reachable. Exiting without any changes."
    touch /dev/shm/picframe_offline.flag
    exit 1
fi

# Server is reachable: Clear offline flag and set download flag
rm -f /dev/shm/picframe_offline.flag
touch /dev/shm/picframe_download.flag

log_msg "Server is online. Starting sync."

# 2. Run Photo Sync
run_sync "photo"

# 3. Run Video Sync (with priority logic)
VIDEO_SYNC_ENABLED=$(get_config "video_sync" "enabled")
if [ "$VIDEO_SYNC_ENABLED" == "true" ]; then
    log_msg "Checking photo quota to decide on video sync..."
    photo_quota_gb=$(get_config "photo_sync" "quota_gb")
    photo_threshold_pct=$(get_config "photo_sync" "video_sync_threshold_pct")
    photo_file_extensions=$(get_config "photo_sync" "file_extensions")
    
    current_photo_size_gb=$(get_media_size_gb "$photo_file_extensions")
    
    # Calculate current percentage of photo quota used
    current_pct=0
    # Use awk for floating point comparison to avoid bc dependency here
    is_full=$(awk -v current="$current_photo_size_gb" -v quota="$photo_quota_gb" 'BEGIN { print (current >= quota) ? 1 : 0 }')

    if [ "$is_full" -eq 1 ]; then
        current_pct=100
    elif (( $(echo "$photo_quota_gb > 0" | bc -l) )); then
        current_pct=$(echo "scale=0; ($current_photo_size_gb * 100) / $photo_quota_gb" | bc)
    fi

    log_msg "Photo quota is at $current_pct% capacity ($current_photo_size_gb GB / $photo_quota_gb GB). Threshold: $photo_threshold_pct%."
    if [ "$current_pct" -ge "$photo_threshold_pct" ]; then
        log_msg "Photo quota is nearly full. Starting video sync."
        run_sync "video"
    else
        log_msg "Photo quota is not full enough. Skipping video sync."
    fi
else
    log_msg "Video sync is disabled. Skipping."
fi

log_msg "Media sync process finished."