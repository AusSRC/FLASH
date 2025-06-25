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
################################################################################################
# Database connection details: edit these as appropiate
HOST="10.0.2.225"
PORT="5432"

# HPC platfom details: edit these as appropiate
PLATFORM="setonix.pawsey.org.au"
USER="ger063"
###############################################################################################
FLASHPASS=$1
MODE=$2

# Query FLASHDB for new sbids
if [ "$MODE" = "INVERT" ]; then
    echo "Querying FLASHDB for inverted detection status"
    python3 ~/src/FLASH/database/db_utils.py -m SBIDSTODETECT -ht $HOST -pt $PORT -i -pw $FLASHPASS > find_invert_detection.log
    output=$( tail -n 1 find_invert_detection.log)
else
    echo "Querying FLASHDB for detection status"
    python3 ~/src/FLASH/database/db_utils.py -m SBIDSTODETECT -ht $HOST -pt $PORT -pw $FLASHPASS > find_detection.log
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

# Get the data for the sbids from the FLASHDB 
cd ~/tmp
for SBID1 in ${SBIDARRAY[@]}; do
    # Make temp download directory
    mkdir "$SBID1"
    echo "Downloading $SBID1 spectral ascii files from database"
    cd $SBID1
    python3 ~/src/FLASH/database/db_download.py -m ASCII -s $SBID1 -ht $HOST -pt $PORT -d ~/tmp/$SBID1 -pw $FLASHPASS
    cd ../
done
echo "Alerting HPC platform $PLATFORM"
if [ "$MODE" = "INVERT" ]; then
    scp ~/src/cronjobs/find_invert_detection.log $USER@$PLATFORM:~/src/cronjobs/
else
    scp ~/src/cronjobs/find_detection.log $USER@$PLATFORM:~/src/cronjobs/
fi
echo "triggering detection_processing.sh on $PLATFORM"
ssh $USER@$PLATFORM "cd ~/src/cronjobs; ./detection_processing.sh $FLASHPASS $MODE &> detection.log"
echo "Done!"
    

