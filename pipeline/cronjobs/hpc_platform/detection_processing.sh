#!/bin/bash

#######################################################################################################
# Edit these for the specific user:
CASDA_EMAIL="user@email"
CASDA_PWD="password_at_CASDA"
ORACLE_DB="TRUE"
#######################################################################################################

FLASHPASS=$1
MODE=$2

output=""
if [ $ORACLE_DB = "TRUE" ]; then
    HOST = "152.67.97.254"
fi
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


# Query FLASHDB for new sbids
if [ "$MODE" = "INVERT" ]; then
    ssh -i $FLASHDB/oracle_flash_vm.key flash@$HOST "cd ~/src/FLASH/database; python3.9 ./db_utils.py -m SBIDSTODETECT -i True -pw $FLASHPASS > ../cronjobs/find_invert_detection.log"
    scp -i $FLASHDB/oracle_flash_vm.key flash@$HOST:/home/flash/src/cronjobs/find_invert_detection.log .
    output=$( tail -n 1 find_detection.log)
else
     ssh -i $FLASHDB/oracle_flash_vm.key flash@$HOST "cd ~/src/FLASH/database; python3.9 $FLASHDB/db_utils.py -m SBIDSTODETECT -pw $FLASHPASS > ../cronjobs/find_detection.log"
    scp -i $FLASHDB/oracle_flash_vm.key flash@$HOST:/home/flash/src/cronjobs/find_detection.log .
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

# Get the data for the sbids from the FLASHDB and process

# Initialise status file
cd $DETECTDIR
echo "for ${SBIDARRAY[@]}:" > $DETECTDIR/jobs_to_sbids.txt

for SBID1 in ${SBIDARRAY[@]}; do
    # Make required config directories and load with ini files
    PARENT1="$PARENT_DIR/$SBID1"
    DIR1="$PARENT1/spectra_ascii"
    mkdir -p "$PARENT1/config"
    # Check if we need to download the data:
    if [ ! -d "$DIR1" ] && [ -z "$( ls -A '$DIR1' )" ]; then
        cd $DBDIR 
        # Download the Linefinder input files from the database, check for bad files
        if [ $ORACLE_DB="TRUE" ]; then
            echo "Using Oracle db"
            jid1=$(/bin/bash $FLASHDB/slurm_run_oracle_db_download.sh $SBID1 $DIR1 $BAD_FILES_DIR $FLASHPASS)
        else
            echo "Using Nimbus db"
            jid1=$(/bin/bash $FLASHDB/slurm_run_db_download.sh $SBID1 $DIR1 $BAD_FILES_DIR $FLASHPASS)
        fi
        # Report
        j1=$(echo $jid1 | awk '{print $4}')
        echo "Sumbitted download job $j1"
        cd $DETECTDIR
        if [ "$MODE" != "INVERT" ]; then 
            cp slurm_linefinder.ini model.txt $PARENT1/config
            jid2=$(sbatch --dependency=afterok:$j1 $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
        j2=$(echo $jid2 | awk '{print $4}')
        echo "Sumbitted dependent detection job $j2"
        echo "$j2 = sbid $SBID1" >> $DETECTDIR/jobs_to_sbids.txt
    else
        cd $DETECTDIR
        cp slurm_linefinder.ini model.txt $PARENT1/config
        jid2=$(sbatch $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
        j2=$(echo $jid2 | awk '{print $4}')
        echo "Sumbitted detection job $j2"
        echo "$j2 = sbid $SBID1" >> $DETECTDIR/jobs_to_sbids.txt
    fi
    cd $CRONDIR
    jid3=$(sbatch --dependency=afterok:$j2 tar_detection_outputs.sh $SBID)
    j3=$(echo $jid3 | awk '{print $4}')
    jid4=$(sbatch --dependency=afterok:$j3 push_detection_to_oracle.sh $SBID)

done
exit

