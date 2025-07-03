#!/bin/bash

######################################################################################################
# Author: GWHG, AusSRC
#
# Date: 20/06/2025
#
# This script runs in response to a cron script running on a client machine (currently at Oracle).
# It checks a local log (put here by the client) for any sbids that require processing.
# If there are any, it retrieves the ASCII input files from the client (via scp) and processes them.
#
# Note that after retrieval, it will delete the files on the client.
#
# It then tars up the outputs, pushes them to the client and initiates a script on the client to
# upload the outputs to the FLASH database (via ssh).

#######################################################################################################
# Edit these for the specific hpc-platform user:
CASDA_EMAIL="user@email"
CASDA_PWD="password_at_CASDA"
ORACLE_DB="TRUE"
CLIENT="152.67.97.254"
#######################################################################################################

FLASHPASS=$1
MODE=$2

output=""
source ~/setonix_set_local_env.sh
# Local directories on setonix:
DBDIR="/home/$USER/src/database/"
DETECTDIR="/home/$USER/src/linefinder/"
if [ "$MODE" = "INVERT" ]; then
    DETECTDIR="/home/$USER/src/inverted_linefinder/"
fi

# The parent directory to hold the SBIDS
PARENT_DIR=$DATA

# Directory to move bad data files to:
BAD_FILES_DIR="$DATA/bad_ascii_files/"

cd $CRONJOBS
# Check logs for new sbids to process
if [ "$MODE" = "INVERT" ]; then
    output=$( tail -n 1 find_invert_detection.log)
else
    output=$( tail -n 1 find_detection.log)
fi
sbids=${output:1: -1}
if test "$output" == "[]"
then
    echo "No sbids to process"
    exit
fi

sbids=$(sed "s/ //g" <<< $sbids)
SBIDS=$(sed "s/,/ /g" <<< $sbids)
echo "SBIDS = $SBIDS"
SBIDARR=()
read -a SBIDARR <<< "$SBIDS"
# Limit size of SBIDARRAY to 10:
SBIDARRAY=()
SBIDARRAY=${SBIDARR[@]:0:10}
echo -e "\nprocessing ${SBIDARRAY[@]}"

# Get the data for the sbids from the client and process

# Initialise status file
cd $DETECTDIR
echo "for ${SBIDARRAY[@]}:" > $DETECTDIR/jobs_to_sbids.txt

for SBID1 in ${SBIDARRAY[@]}; do
    # Make required config directories and load with ini files
    PARENT1="$PARENT_DIR/$SBID1"
    DIR1="$PARENT1/spectra_ascii"
    mkdir -p "$PARENT1/config"
    # Get the ASCII data from the client:
    scp flash@$CLIENT:~/tmp/$SBID1/$SBID1*.tar.gz $DIR1/
    # Delete ASCII directory on client:
    ssh flash@$CLIENT "cd ~/tmp; rm -R $SBID1"
    # Untar ASCII tarball
    cd $DIR1; tar -zxvf $SBID*.tar.gz;rm $SBID*.tar.gz

    # Check for bad (all NaN values) files, move them to bad files directory
    echo "Checking for bad files"
    python $FINDER/pre_process.py '$BAD_FILES_DIR' '$DIR1'

    # Process the files
    cd $DETECTDIR
    cp slurm_linefinder*.ini model.txt $PARENT1/config
    jid2=$(sbatch $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
    j2=$(echo $jid2 | awk '{print $4}')
    echo "Sumbitted detection job $j2"
    echo "$j2 = sbid $SBID1" >> $DETECTDIR/jobs_to_sbids.txt

    # Tar up results and send them back to the client for upload to the FLASH db
    cd $CRONDIR
    if [ "$MODE" = "INVERT" ]; then
        jid3=$(sbatch --dependency=afterok:$j2 tar_detection_inverted_outputs.sh $SBID)
        j3=$(echo $jid3 | awk '{print $4}')
        jid4=$(sbatch --dependency=afterok:$j3 push_detection_inverted_to_oracle.sh $SBID)

    else
        jid3=$(sbatch --dependency=afterok:$j2 tar_detection_outputs.sh $SBID)
        j3=$(echo $jid3 | awk '{print $4}')
        jid4=$(sbatch --dependency=afterok:$j3 push_detection_to_oracle.sh $SBID)
fi

done
exit

