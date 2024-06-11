#!/bin/bash
FLASHPASS=$1

# Local directories
DBDIR="/home/ger063/src/database/"
DETECTDIR="/home/ger063/src/flashfinder_local_mpi/"

# The parent directory to hold the SBIDS
PARENT_DIR="/scratch/ja3/ger063/data/casda/"

# Directory to move bad data files to:
BAD_FILES_DIR="/scratch/ja3/ger063/data/casda/bad_ascii_files/"

source ~/setonix_set_local_env.sh

# Query FLASHDB for new sbids
python3.9 $FLASHDB/db_utils.py -m SBIDSTODETECT -pw $FLASHPASS > find_detection.log
output=$( tail -n 1 find_detection.log)
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
    # Check if we need to download the data:
    if [ ! -d "$DIR1" ]; then
        cd $DBDIR 
        # Download the Linefinder input files from the database, check for bad files
        jid1=$(/bin/bash $FLASHDB/slurm_run_db_download.sh $SBID1 $DIR1 $BAD_FILES_DIR $FLASHPASS)
        # Report
        j1=$(echo $jid1 | awk '{print $4}')
        echo "Sumbitted download job $j1"
        cd $DETECTDIR
        mkdir -p "$PARENT1/config"
        cp slurm_linefinder.ini model.txt $PARENT1/config
        jid2=$(sbatch --dependency=afterok:$j1 $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
        j2=$(echo $jid2 | awk '{print $4}')
        echo "Sumbitted dependent detection job $j2"
        echo "$j2 = sbid $SBID1" >> $DETECTDIR/jobs_to_sbids.txt
    else
        cd $DETECTDIR
        mkdir -p "$PARENT1/config"
        cp slurm_linefinder.ini model.txt $PARENT1/config
        jid2=$(sbatch $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
        j2=$(echo $jid2 | awk '{print $4}')
        echo "Sumbitted detection job $j2"
        echo "$j2 = sbid $SBID1" >> $DETECTDIR/jobs_to_sbids.txt
    fi
    

done
exit

