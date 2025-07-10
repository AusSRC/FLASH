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
ORACLE_KEY="~/.ssh/oracle_flash_vm.key"
ORACLE_DB="TRUE"
CLIENT="152.67.97.254"
TMP_ON_CLIENT=/mnt/tmp

CRONDIR=$HOME/src/cronjobs/
#######################################################################################################

FLASHPASS=$1
MODE=$2

USELOGFILE=true
DETECTLOG="find_detection.log"
if [ "$MODE" = "INVERT" ]; then
    DETECTLOG="find_invert_detection.log"
fi

# Check if we were passed an sbid to process - if not it is read from the 'find_detection' logfile
if [ "$#" -gt 2 ]; then
    USELOGFILE=false
    SBIDARR=( "$@" )
    SBIDARRAY=${SBIDARR[@]:2}
    CHECKDB=false
    rm $DETECTLOG
    printf "For inversion:\nSBIDS that need detection analysis\n[" > $DETECTLOG
    for SBID1 in ${SBIDARRAY[@]}; do
        printf "$SBID1, " >> $DETECTLOG
    done
    sed -i '$ s/.$//' $DETECTLOG
    sed -i '$ s/.$/]/' $DETECTLOG
     
fi

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

cd $CRONDIR
# If sbids were not provided, check logs for new sbids to process
if [ "$USELOGFILE" = true ]; then
    output=$( tail -n 1 $DETECTLOG)
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
fi

echo -e "\nprocessing ${SBIDARRAY[@]}"

# Initialise status file
cd $DETECTDIR
echo "for ${SBIDARRAY[@]}:" > $DETECTDIR/jobs_to_sbids.txt

for SBID1 in ${SBIDARRAY[@]}; do
    
    # Make required config directories and load with ini files
    PARENT1="$PARENT_DIR/$SBID1"
    DIR1="$PARENT1/spectra_ascii"
    mkdir -p "$PARENT1/config"
    mkdir -p "$DIR1"
    # Untar ASCII tarball
    cd $DIR1; tar -zxf $SBID*.tar.gz;rm $SBID*.tar.gz

    # Process the files
    cd $DETECTDIR
    cp slurm_linefinder*.ini model.txt $PARENT1/config
    # Create parameter string for sbatch:
    jid2=0
    if [ "$MODE" = "INVERT" ]; then
        SBATCHARGS="--time 12:00:00 --ntasks 100 --ntasks-per-node 20 --no-requeue --output $PARENT1/logs/out_inverted.log --error $PARENT1/logs/err_inverted.log --job-name INV_$SBID1"
        jid2=$(sbatch $SBATCHARGS $FINDER/slurm_run_flashfinder_inverted.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
    else
        SBATCHARGS="--time 12:00:00 --ntasks 100 --ntasks-per-node 20 --no-requeue --output $PARENT1/logs/out.log --error $PARENT1/logs/err.log --job-name STD_$SBID1"
        jid2=$(sbatch $SBATCHARGS $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
    fi
    j2=$(echo $jid2 | awk '{print $4}')
    echo "Sumbitted detection job $j2"
    echo "$j2 = sbid $SBID1" >> $DETECTDIR/jobs_to_sbids.txt

    # Tar up results and send them back to the client for upload to the FLASH db
    cd $CRONDIR
    if [ "$MODE" = "INVERT" ]; then
        jid3=$(sbatch --dependency=afterok:$j2 tar_detection_inverted_outputs.sh $SBID1)
        j3=$(echo $jid3 | awk '{print $4}')
        jid4=$(sbatch --dependency=afterok:$j3 push_detection_inverted_to_oracle.sh $SBID1)

    else
        jid3=$(sbatch --dependency=afterok:$j2 tar_detection_outputs.sh $SBID1)
        j3=$(echo $jid3 | awk '{print $4}')
        jid4=$(sbatch --dependency=afterok:$j3 push_detection_to_oracle.sh $SBID1)
    fi

done
echo "Processing started for sbids:"
echo ${SBIDARRAY[@]}
exit

