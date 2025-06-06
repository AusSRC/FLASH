#!/bin/bash
IFS=","
FLASHPASS=$1

# Local directories
DBDIR="/home/ger063/src/database"
DETECTDIR="/home/ger063/src/linefinder"

# The parent directory to hold the SBIDS
PARENT_DIR="/scratch/ja3/ger063/data/casda"

# Directory to move bad data files to:
BAD_FILES_DIR="/scratch/ja3/ger063/data/casda/bad_ascii_files"

source ~/setonix_set_local_env.sh

IFS=" "
SBIDARRAY=(34556 34557 34558 34559 34560 34561 34562 34563 34564 34565)
SBIDARRAY=(67216 67191 67190 67189 67185 67178 66981 66980)
echo "Processing: ${SBIDARRAY[@]}"

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
    # Pilot survey data from the db is stored at a different path:
    jid2=$(sbatch --nodes=1 --ntasks-per-node=1 --cpus-per-task=1 --dependency=afterok:$j1 --wrap "mv $DIR1/scratch/ja3/ger063/data/$SBID1/spectra_ascii/* $DIR1")
    j2=$(echo $jid2 | awk '{print $4}')
    echo "Sumbitted dependent move job $j2"

    cd $DETECTDIR
    mkdir -p $PARENT1/config
    cp slurm_linefinder.ini model.txt $PARENT1/config
    jid3=$(sbatch --dependency=afterok:$j2 $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
    j3=$(echo $jid3 | awk '{print $4}')
    echo "Sumbitted dependent detection job $j3"
    echo "$j3 = sbid $SBID1" >> jobs_to_sbids.txt
    

done
exit
