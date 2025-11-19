#!/bin/bash
# Run daily on weekdays to delete old session folders older than 1 day.
# add to crontab with:
# m h  dom mon dow   command
# 00 00 * * 1-5 /bin/bash /home/flash/src/cronjobs/oracle_casda_update.sh

BASE_DIR="$(dirname "$0")"
TMP_ROOT=$(realpath "$BASE_DIR/db_query/static/db_query")
EXPIRE_SECONDS=86400
NOW=$(date +%s)

cleanup_folder() {
    local folder=$1
    if [ -d "$folder" ]; then
        MOD_TIME=$(stat -c %Y "$folder")
        AGE=$(( NOW - MOD_TIME ))

        if [ $AGE -gt $EXPIRE_SECONDS ]; then
            echo "Deleting old session folder: $folder"
            rm -rf "$folder"
        fi
    fi
}

# List of specific subfolders to clean
SUBFOLDERS=("plots" "linefinder" "linefinder/masks" "ascii")
echo "Starting cleanup of session folders older than 1 day..."
for sub in "${SUBFOLDERS[@]}"; do
    TARGET="$TMP_ROOT/$sub"
    if [ -d "$TARGET" ]; then
        # Loop through session ID folders inside this subfolder
        for session_folder in "$TARGET"/*; do
            if [ -d "$session_folder" ]; then
                cleanup_folder "$session_folder"
            fi
        done
    fi
done
echo "Cleanup for old sessions complete."