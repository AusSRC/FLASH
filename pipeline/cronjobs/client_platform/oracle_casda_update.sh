#!/bin/bash


#######################################################################################################
# Edit these for the specific user:
CASDA_EMAIL="user@email"
CASDA_PWD="password_at_CASDA"
HPC_PLATFORM="setonix.pawsey.org.au"
HPC_USER="user_at_hpc"
HPC_SCRATCH="/scratch/ja3/$HPC_USER/data/casda"
#######################################################################################################

IFS=","
FLASHPASS=$1



# Local directories:

# The tag to give the data: eg "FLASH Survey 1", or "FLASH Pilot2" etc
TAG="FLASH Survey 1"

echo "Querying CASDA"
# Query CASDA for new sbids
python3 $FLASHDB/db_utils.py -m GETNEWSBIDS -e $CASDA_EMAIL -p $CASDA_PWD -pw $FLASHPASS -r > $CRONDIR/new_sbids.log
output=$( tail -n 1 $CRONDIR/new_sbids.log)
sbids=${output:1: -1}
if test "$output" == "[]"
then
    echo "No sbids to process"
    exit
else
    echo "Starting spectral processing of new SBIDS at $HPC_PLATFORM"
fi

scp $CRONDIR/new_sbids.log $HPC_USER@$HPC_PLATFORM:~/src/cronjobs

# Copy across the SBID data to HPC
sbids=$(sed "s/ //g" <<< $sbids)
sbids="${sbids//\'}"
SBIDS=$(sed "s/,/ /g" <<< $sbids)
IFS=" "
SBIDARRAY=()
read -a SBIDARRAY <<< "$SBIDS"
echo "downloaded: $SBIDS"
for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"
    scp -r $DATA/$SBID $HPC_USER@$HPC_PLATFORM:$HPC_SCRATCH/
done

# Trigger spectral processing on HPC
ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/cronjobs; ./casda_download_and_spectral.sh &> spectral.log;" 
scp $HPC_USER@$HPC_PLATFORM:~/src/cronjobs/spectral.log /home/flash/src/cronjobs/
