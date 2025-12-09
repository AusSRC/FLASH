#!/bin/bash

################################################################################################
# Author: GWHG, AusSRC
#
# Date: 20/06/2025
#
# This script runs on the client VM (the one running the crontab) and is called by cron.
# It checks for two types of failed jobs for the given mode (STD, INVERT or MASK) on the 
# HPC platform and reruns them.
#
# These are jobs that reached walltime but hadn't finished, or jobs that sufffered an MPI
# interconnect error and were automatically cancelled.
# 
# It first checks for two logs on the HPC_PLATFORM  - 'failed_sbids.txt' and 'error_mpi_sbids.txt'.
#
# If they exist they are scp'd back to the client and sbids extracted from them. Those sbids are 
# checked against the FLASHDB (in case they were manually rerun and the logs weren't removed),
# and if the database shows them as not processed they are submitted for rerunning.
#
# It downloads requisite ASCII files from the database and sends the 
# list of sbids to the HPC platform.
# It then triggers a linefinder job on the HPC platform.
#
# The HPC platform is responsible for getting the ASCII files from the client,
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
MASKDIR="$HOME/src/cronjobs/masks"

###############################################################################################
MODE=$1
CHECKDB=true
LIMIT=6

SBIDARR=()
SBIDARY=()
SBIDARRAY=()
FAILEDSBIDS=()
SBIDMASKS=""
STATUSLOG="status.log"

SBIDS=()
num_jobs=0
# Check for the last jobs run:

JOBS=`ls ${MODE}_detection_*.log`
for i in $JOBS; do 
    sbid=`echo $i | tr -d -c 0-9`
    SBIDS+=($sbid)
    ((num_jobs++))
done

# Generate any $MODE error logs on the HPC platform:
if [[ "$num_jobs" -gt 0 ]]; then
    echo "Generating report for $MODE detection jobs"
    echo "SBIDS = ${SBIDS[@]}"
    ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/linefinder; ./check_progress.sh $MODE s ${SBIDS[@]}"
else
    echo "No $MODE detection jobs run"
fi

WALLEDLOG="${MODE}_failed_sbids.sh"
MPIERRLOG="${MODE}_error_mpi_sbids.sh"

# Remove old logs
rm $WALLEDLOG $MPIERRLOG


# Get the error logs from the HPC_PLATFORM
scp $HPC_USER@$HPC_PLATFORM:~/src/linefinder/$WALLEDLOG /home/flash/src/cronjobs/
scp $HPC_USER@$HPC_PLATFORM:~/src/linefinder/$MPIERRLOG /home/flash/src/cronjobs/
# Delete them from the HPC_PLATFORM
ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/linefinder; rm $WALLEDLOG $MPIERRLOG"

if [ -f "$WALLEDLOG" ]; then
    source $WALLEDLOG
    FAILEDSBIDS+=("${failed[@]}")
fi
if [ -f "$MPIERRLOG" ]; then
    source $MPIERRLOG
    FAILEDSBIDS+=("${error[@]}")
fi

echo "Failed: ${FAILEDSBIDS[@]}"

# Limit number of sbids we process
FAILEDSBIDS=("${FAILEDSBIDS[@]:0:$LIMIT}")

echo "Indicated as failed: ${FAILEDSBIDS[@]}"
echo " ... checking database"

DETECTLOG="find_detection.log"
if [ "$MODE" = "INVERT" ]; then
    DETECTLOG="find_invert_detection.log"
elif [ "$MODE" = "MASK" ]; then
    DETECTLOG="find_mask_detection.log"
elif [ "$MODE" = "TEST" ]; then
    DETECTLOG="test_detection.log"
fi

# Query FLASHDB for status of sbids
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
    SBIDARR="${SBIDARY[@]}"
fi

# Compare FAILEDSBIDS with SBIDARR from the database - common element to REPROCESS
REPROCESS=()
for i in "${FAILEDSBIDS[@]}"; do
    if [[ " ${SBIDARR[*]} " =~ " $i " ]]; then
        REPROCESS+=($i)
    fi
done
echo "To re-process: ${REPROCESS[@]}"

# Initialise status file on hpc
STATUSFILE="jobs_to_sbids.txt"
if [ "$MODE" != "TEST" ]; then
    ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/linefinder; echo ${REPROCESS[@]} > $STATUSFILE"
fi

#echo -e "\nprocessing\n ${SBIDARRAY[@]}"
# Get the data for the sbids from the FLASHDB 
cd $TMPDIR
#for SBID1 in ${SBIDARRAY[@]}; do
for SBID1 in ${REPROCESS[@]}; do
    # Can't run an INVERT or MASK job if STD detection hasn't been done
    python3 ~/src/FLASH/database/db_utils.py -m CHECK_SBIDS -s $SBID1 -sm INVERT -ht $HOST -pt $PORT -pw $FLASHPASS > $STATUSLOG
    output=$( head -n 3 $STATUSLOG)
    flags=( ${output[@]} )
    stdF=${flags[0]}
    invertF=${flags[1]}
    maskF=${flags[2]}
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
        scp $HPC_USER@$HPC_PLATFORM:~/src/cronjobs/${MODE}_detection_${SBID1}.log /home/flash/src/cronjobs/
        ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/cronjobs; rm ${MODE}_detection_${SBID1}.log"
    fi
    cd ../
done
echo "Done!"
    

