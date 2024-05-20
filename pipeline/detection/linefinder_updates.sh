#!/bin/bash
IFS=","
FLASHPASS=$1

# Local directories
DBDIR="~/src/database"
DETECTDIR="~/src/flashfinder_local_mpi"

# The parent directory to hold the SBIDS
PARENT_DIR="/scratch/ja3/ger063/data/casda"

# Directory to move bad data files to:
BAD_FILES_DIR="/scratch/ja3/ger063/data/casda/bad_ascii_files"

source ~/setonix_set_local_env.sh

# Query CASDA for new sbids
python3.9 $FLASHDB/db_utils.py -m SBIDSTODETECT -pw aussrc > find_detection.log
output=$( tail -n 1 find_detection.log)
sbids=${output:1: -1}
if test "$output" == "[]"
then
    echo "No sbids to process"
    exit
fi

sbids=$(sed "s/ //g" <<< $sbids)
sbids="${sbids//\'}"
SBIDS=$(sed "s/,/ /g" <<< $sbids)
IFS=" "
SBIDARRAY=()
read -a SBIDARRAY <<< "$SBIDS"
echo "downloaded: $SBIDS"

# Get the data for the sbids from the FLASHDB and process

# Initialise status file
echo "for $SBIDS:" > $DETECTDIR/jobs_to_sbids.txt

for SBID1 in "${SBIDARRAY[@]}"; do
    cd $DBDIR
    # Make required config directories and load with ini files
    PARENT1=$PARENT_DIR/$SBID1
    DIR1=$PARENT1/spectra_ascii
    mkdir -p $PARENT1/config
    # Download the Linefinder input files from the database, check for bad files
    jid1=$(/bin/bash $FLASHDB/slurm_run_db_download.sh $SBID1 $DIR1 $BAD_FILES_DIR $FLASHPASS)
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted download job $j1"
    cd $DETECTDIR
    mkdir -p $PARENT1/config
    cp slurm_linefinder.ini model.txt $PARENT1/config
    jid2=$(sbatch --dependency=afterok:$j1 $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
    j2=$(echo $jid2 | awk '{print $4}')
    echo "Sumbitted dependent detection job $j2"
    echo "$j2 = sbid $SBID1" >> jobs_to_sbids.txt
    

done
exit

# Process the sbids
cd $DETECTDIR/slurm/
echo "submitting LINEFINDER jobs"
echo


for SBID1 in "${SBIDARRAY[@]}"; do
    PARENT1=$PARENT_DIR/$SBID1
    cp slurm_linefinder.ini model.txt $PARENT1/config
     # pass to slurm_run scripts: 
    jid1=$(/bin/bash $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $EXCLUDE)
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted job $j1"
    echo "$j1 = sbid $SBID1" >> jobs_to_sbids.txt
done

