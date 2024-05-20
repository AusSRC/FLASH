#!/bin/bash
######################################################################################
######################################################################################
#
#       Download ascii files from database to use in Linefinder run
#
#   This script will perform the following:
#       1. Create required subdirectories
#       2. Download the required linefinder input ASCII files from the FLASH database
#       3. Move any ASCII files that are all NaN in value, or have malformed lines
#
#   NOTE:   The script calling order is:
#               1) "run_db_download.sh", which calls:
#                   2) "slurm_run_db_download.sh"
#
#       The script expects a parent directory to exist ("PARENT_DIR", see below), under 
#       which it will create all required sub-directories.
#
#       This requires the FLASHDB password to be passed on the command line eg:
#               ./run_db_download.sh my_password


####################### USER EDIT VALUES #############################################
FLASHPASS=$1
# The SBIDS to process:
SBIDARRAY=(52618)

# The parent directory holding the SBIDS
PARENT_DIR="/scratch/ja3/ger063/data/casda"

# Directory to move bad data files to:
BAD_FILES_DIR="/scratch/ja3/ger063/data/casda/bad_ascii_files"


#####################################################################################
############### DO NOT EDIT FURTHER #################################################

source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh

for SBID1 in "${SBIDARRAY[@]}"; do
    # Make required config directories and load with ini files
    PARENT1=$PARENT_DIR/$SBID1
    DIR1=$PARENT1/spectra_ascii
    mkdir -p $PARENT1/config
    # Download the Linefinder input files from the database, check for bad files
    jid1=$(/bin/bash $FLASHDB/slurm_run_db_download.sh $SBID1 $DIR1 $BAD_FILES_DIR $FLASHPASS)
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted download job $j1"

done

