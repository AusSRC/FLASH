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
# This script is run with two required arguments: $1 = flashdb password, $2 = MODE 
# (one of DETECT, INVERT or MASK)
#
# If further args are given, they are assumed to be sbid numbers (space separated). If this is the
# case, the database is not checked for sbids to process.
################################################################################################
# Database connection details: edit these as appropiate
HOST="10.0.2.225"
PORT="5432"
# Client platform details: : edit these as appropiate
source $HOME/set_local_env.sh

# HPC platform details: edit these as appropiate
PLATFORM="setonix.pawsey.org.au"
USER="ger063"
HPC_DATA="/scratch/ja3/$USER/data/casda"
###############################################################################################
FLASHPASS=$1
MODE=$2
CHECKDB=true

DETECTLOG="find_detection.log"
if [ "$MODE" = "INVERT" ]; then
    DETECTLOG="find_invert_detection.log"
fi

# Check if we were passed sbids to process, or we need to check the db
if [ "$#" -gt 2 ]; then
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
# Query FLASHDB for new sbids
if [ "$CHECKDB" = true ]; then
    if [ "$MODE" = "INVERT" ]; then
        echo "Querying FLASHDB for inverted detection status"
        python3 ~/src/FLASH/database/db_utils.py -m SBIDSTODETECT -ht $HOST -pt $PORT -i -pw $FLASHPASS > $DETECTLOG
        output=$( tail -n 1 $DETECTLOG)
    else
        echo "Querying FLASHDB for detection status"
        python3 ~/src/FLASH/database/db_utils.py -m SBIDSTODETECT -ht $HOST -pt $PORT -pw $FLASHPASS > $DETECTLOG
        output=$( tail -n 1 $DETECTLOG)
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
    # Limit size of SBIDARRAY to 6:
    SBIDARRAY=()
    SBIDARRAY=${SBIDARR[@]:0:6}
fi
echo -e "\nprocessing ${SBIDARRAY[@]}"
# Get the data for the sbids from the FLASHDB 
cd $TMPDIR
for SBID1 in ${SBIDARRAY[@]}; do
    # Make temp download directory
    mkdir "$SBID1"
    echo "Downloading $SBID1 spectral ascii files from database"
    cd $SBID1
    python3 ~/src/FLASH/database/db_download.py -m ASCII -s $SBID1 -ht $HOST -pt $PORT -d $TMPDIR/$SBID1 -pw $FLASHPASS
    echo "Sending $SBID1 ASCII tarball to $PLATFORM"
    ssh $USER@$PLATFORM "mkdir -p $HPC_DATA/$SBID1/spectra_ascii; rm $HPC_DATA/$SBID1/spectra_ascii/*;"
    scp $TMPDIR/$SBID1/*$SBID1*.tar.gz $USER@$PLATFORM:$HPC_DATA/$SBID1/spectra_ascii
    
    echo "Alerting HPC platform $PLATFORM"
    scp ~/src/cronjobs/$DETECTLOG $USER@$PLATFORM:~/src/cronjobs/
    echo "triggering detection_processing.sh on $PLATFORM"
    ssh $USER@$PLATFORM "cd ~/src/cronjobs; ./detection_processing.sh $FLASHPASS $MODE $SBID1 &> detection_$SBID1.log"
    scp $USER@$PLATFORM:~/src/cronjobs/detection_$SBID1.log /home/flash/src/cronjobs/
    cd ../
done
echo "Done!"
    

