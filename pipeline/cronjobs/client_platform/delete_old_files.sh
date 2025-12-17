#!/bin/bash
# Run daily on weekdays to delete old session folders older than 1 day.
# add to crontab with:
# m h  dom mon dow   command
# 00 00 * * 1-5 /bin/bash /home/flash/src/cronjobs/delete_old_files.sh

BASE_DIR="$HOME/src/FLASH/django/flashdb"
TMP_ROOT="$BASE_DIR/db_query/static/db_query"

# List of specific subfolders to clean
SUBFOLDERS=("plots" "linefinder" "linefinder/masks" "ascii")
echo "Starting cleanup of session folders older than 1 day..."

for sub in "${SUBFOLDERS[@]}"; do
    TARGET="$TMP_ROOT/$sub"
    # delete all folders older than 1 day
    # take care not to delete "masks" subfolder in linefinder
    find "$TARGET" -mindepth 1 -type d -not -name "masks" -mtime +1 -exec rm -rf {} +
done

echo "Cleanup for old sessions complete."