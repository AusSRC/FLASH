#!/bin/bash

################################################################################################
# Author: GWHG, AusSRC
#
# Date: 20/06/2025
#
# This script runs on the client VM (the one running the crontab) and is called by cron. 
# It first checks the FLASHDB database to see if any sbids need detection or inverted detection
# processing.
#
# If not it exits. Otherwise it downloads requisite ASCII files from the database and sends the 
# list of sbids to the HPC platform.
# It then triggers a linefinder job on the HPC platform.
#
# The HPC platform is responsible for getting the ASCII files from the clinet,
# processing them and pushing the results back to the client and initiating a 
# database upload. This is done (on the HPC platform) by "detection_processing.sh"
#
# This script is run with one required argument: $1 = MODE (one of STD, INVERT or MASK)
#
# If further args are given, they are assumed to be sbid numbers (space separated). If this is the
# case, the database is not checked for sbids to process.
################################################################################################
# Client platform details: : edit these as appropiate
source $HOME/set_local_flash_env.sh

# For masked detection, provide the directory that holds the mask files
MASKDIR="$CRONDIR/masks"

###############################################################################################
MODE=$1
LIMIT=6
CHECKDB=true

SBIDARR=()
SBIDARY=()
SBIDARRAY=()
SBIDMASKS=""
STATUSLOG="status.log"

DETECTLOG="find_detection.log"
if [ "$MODE" = "INVERT" ]; then
    DETECTLOG="find_invert_detection.log"
elif [ "$MODE" = "MASK" ]; then
    DETECTLOG="find_mask_detection.log"
elif [ "$MODE" = "TEST" ]; then
    DETECTLOG="test_detection.log"
fi

# Check if we were passed sbids to process, or we need to check the db
if [ "$#" -gt 1 ]; then
    SBIDARR=( "${@:2}" )
    CHECKDB=false
    echo "Got cmd line sbids ${SBIDARR[@]}"
    # For masked detection, only process if there is a matching mask file
    if [ "$MODE" = "MASK" ]; then
        MASKFILES=$(printf '%s ' $MASKDIR/SB*.txt)
        SBIDSTR=($(echo "$MASKFILES" | grep -oE '[0-9]+'))
        for item1 in "${SBIDSTR[@]}"; do
            for item2 in "${SBIDARR[@]}"; do
                if [[ "$item1" == "$item2" ]]; then
                    SBIDARY+=("$item1")
                    break
                fi
            done
        done
        SBIDARR=()
        SBIDARR=( "${SBIDARY[@]}" )
        if [ ${#SBIDARR[@]} -eq 0 ]; then
            echo "No mask file(s) found for processing"
            exit
        else
            echo "sbids with valid masks are: ${SBIDARR[@]}"
        fi
    fi
    SBIDARRAY="${SBIDARR[@]:0:$LIMIT}"

fi
# Query FLASHDB for new sbids
if [ "$CHECKDB" = true ]; then
    echo "Querying FLASHDB for $MODE detection status"
    python3 ~/src/FLASH/database/db_utils.py -m SBIDSTODETECT -sm $MODE -ht $HOST -pt $PORT -pw $FLASHPASS > $DETECTLOG
    output=$( tail -n 1 $DETECTLOG)

    sbids=${output:1: -1}
    if test "$output" == "[]"
    then
        echo "No sbids to process"
        exit
    fi
    sbids=$(sed "s/ //g" <<< $sbids)
    SBIDS=$(sed "s/,/ /g" <<< $sbids)
    echo "$MODE not processed for database SBIDS = $SBIDS"
    SBIDARR=()
    read -a SBIDARR <<< "$SBIDS"

    # For masked detection, only process if there is a matching mask file
    if [ "$MODE" = "MASK" ]; then
        MASKFILES=$(printf '%s ' $MASKDIR/SB*.txt)
        SBIDSTR=($(echo "$MASKFILES" | grep -oE '[0-9]+'))
        for item1 in "${SBIDSTR[@]}"; do
            for item2 in "${SBIDARR[@]}"; do
                if [[ "$item1" == "$item2" ]]; then
                    SBIDARY+=("$item1")
                    break
                fi
            done
        done
        SBIDARR=()
        SBIDARR=("${SBIDARY[@]}")
    fi
    # Limit size of SBIDARRAY to LIMIT:
    echo -e "\nLimiting array to $LIMIT"
    SBIDARRAY=${SBIDARR[@]:0:$LIMIT}
    echo "${SBIDARRAY[@]}"
    
fi

rm $DETECTLOG
printf "For $MODE detection:\nSBIDS that need detection analysis\n[" > $DETECTLOG
for SBID1 in ${SBIDARRAY[@]}; do
    printf "$SBID1, " >> $DETECTLOG
done
sed -i '$ s/.$//' $DETECTLOG
sed -i '$ s/.$/]/' $DETECTLOG

# Initialise status file on hpc
STATUSFILE="jobs_to_sbids.txt"
if [ "$MODE" != "TEST" ]; then
    ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/linefinder; echo ${SBIDARRAY[@]} > $STATUSFILE"
fi

echo -e "\nprocessing\n ${SBIDARRAY[@]}"
# Get the data for the sbids from the FLASHDB 
cd $TMPDIR
for SBID1 in ${SBIDARRAY[@]}; do
    python3 ~/src/FLASH/database/db_utils.py -m CHECK_SBIDS -s $SBID1 -sm INVERT -ht $HOST -pt $PORT -pw $FLASHPASS > $STATUSLOG
    output=$( head -n 3 $STATUSLOG)
    flags=( ${output[@]} )
    stdF=${flags[0]}
    invertF=${flags[1]}
    maskF=${flags[2]}
    # Can't run an INVERT or MASK job if STD detection hasn't been done
    if [ "$MODE" != "STD" ] && [ "$MODE" != "TEST" ] && [ "$stdF" = "False" ]; then
        echo "Cant do $MODE processing on $SBID1, as STD detection not done! - Skipping"
        continue
    fi 
    
    # Make temp download directory
    mkdir "$SBID1"
    echo "Downloading $SBID1 spectral ascii files from database"
    cd $SBID1
    python3 ~/src/FLASH/database/db_download.py -m ASCII -s $SBID1 -ht $HOST -pt $PORT -d $TMPDIR/$SBID1 -pw $FLASHPASS
    if [ "$MODE" != "TEST" ]; then
        echo "Sending $SBID1 ASCII tarball to $HPC_PLATFORM"
        ssh $HPC_USER@$HPC_PLATFORM "mkdir -p $HPC_SCRATCH/$SBID1/spectra_ascii; mkdir -p $HPC_SCRATCH/$SBID1/config; rm $HPC_SCRATCH/$SBID1/spectra_ascii/* $HPC_SCRATCH/$SBID1/config/*;"
        scp $TMPDIR/$SBID1/*$SBID1*.tar.gz $HPC_USER@$HPC_PLATFORM:$HPC_SCRATCH/$SBID1/spectra_ascii

        # If masking, we need to transfer the mask file to the HPC:
        if [ "$MODE" = "MASK" ]; then
            scp ~/src/cronjobs/masks/*"$SBID1"_mask.txt $HPC_USER@$HPC_PLATFORM:$HPC_SCRATCH/$SBID1/config/mask.txt
            echo "Sent mask file to HPC platform $HPC_PLATFORM"
        fi
    
        echo "triggering detection_processing.sh on $HPC_PLATFORM"
        ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/cronjobs; ./detection_processing.sh $MODE $SBID1 > ~/src/cronjobs/'$MODE'_detection_$SBID1.log"
        scp $HPC_USER@$HPC_PLATFORM:~/src/cronjobs/${MODE}_detection_${SBID1}.log $CRONDIR
        ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/cronjobs; rm ${MODE}_detection_${SBID1}.log"
    fi
    cd ../
done
echo "Done! Sent ${SBIDARRAY[@]}"
echo "For processing"
    

