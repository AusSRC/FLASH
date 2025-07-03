#!/bin/bash


#######################################################################################################
# Edit these for the specific client-platform user:
CASDA_EMAIL="user@email"
CASDA_PWD="password_at_CASDA"

# Edit these for the specific hpc-platform user:
HPC_PLATFORM="setonix.pawsey.org.au"
HPC_USER="user_at_hpc"
HPC_SCRATCH="/scratch/ja3/$HPC_USER/data/casda"
#######################################################################################################
source $HOME/set_local_env.sh

IFS=","
FLASHPASS=$1

echo "Querying CASDA"
# Query CASDA for new sbids, but don't download anything
python3 $FLASHDB/db_utils.py -m GETNEWSBIDS -e $CASDA_EMAIL -p $CASDA_PWD -pw $FLASHPASS -r -n > $CRONDIR/new_sbids.log
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

# Trigger spectral processing on HPC
ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/cronjobs; ./casda_download_and_spectral.sh &> spectral.log;" 
scp $HPC_USER@$HPC_PLATFORM:~/src/cronjobs/spectral.log /home/flash/src/cronjobs/
