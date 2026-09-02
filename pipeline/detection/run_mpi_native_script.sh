#!/bin/bash
######################################################################################
######################################################################################
#
#       Run FLASH Linefinder MPI on SLURM resource
#
#   This script will perform the following:
#       1. Copy ini files from working directory into appropriate config directories
#       2. Run the linefinder on each SBID simultaneously
#
#   It assumes you have already put the input files (ascii source files) in the correct
#   directory on /scratch, and that all the required sub-directories on /scratch exist.
#
#   NOTE:   The script calling order is:
#               1) "run_mpi_native_script.sh", which calls:
#                   2) "slurm_run_flashfinder.sh"
#
#       The script expects a parent directory to exist ("PARENT_DIR", see below), under 
#       which it will create all required sub-directories.
#
#       It also expects the following files to be in the current working directory:
#               1. run_mpi_native_script.sh (this file)
#               2. slurm_linefinder.ini (the linefinder initialisation file)
#               3. model.txt (the linefinder model parameters)
#
######################################################################################
######################################################################################
####################### USER EDIT VALUES #############################################
source ~/set_local_flash_env.sh
MODE=$1

# The SBIDS to process (if not pass on the command line):
if [ $# -lt 2 ]; then
    rm jobs_to_sbids.txt
    # Add your sbids here
    SBIDARRAY=(55247 55398 55460)
else
    SBIDARRAY=( "${@:2}" )
fi
echo "${SBIDARRAY[@]}"


# The parent directory holding the SBIDS
PARENT_DIR=$DATA

# Local directories on setonix:
DBDIR="/home/$USER/src/database/"
DETECTDIR="/home/$USER/src/linefinder/"
MASKDIR="$DETECTDIR/masks"

# Directory to move bad data files to:
BAD_FILES_DIR="$DATA/bad_ascii_files"


#####################################################################################
############### DO NOT EDIT FURTHER #################################################


for SBID1 in "${SBIDARRAY[@]}"; do
    PARENT1=$PARENT_DIR/$SBID1
    mkdir -p $PARENT1/config
    cp slurm_linefinder*.ini model.txt $PARENT1/config
    # If masking, check that the mask file exists and copy it to SLURM directory
    if [[ "$MODE" =~ ^("MASK"|"INVMASK")$ ]]; then
        if ! ls $MASKDIR/*$SBID1_mask.txt 1> /dev/null 2>&1; then
            echo "$SBID1 mask file not found!! Skipping"
            continue
        else
            cp $MASKDIR/*$SBID1_mask.txt "${PARENT1}/config/mask.txt"
        fi
    fi 

    # pass to slurm_run scripts: 
    if [ "$MODE" = "STD" ]; then
        SBATCHARGS="--exclude=nid00[2024-2055],nid00[2792-2823] --time 12:00:00 --ntasks 100 --ntasks-per-node 20 --no-requeue --output $PARENT1/logs/out.log --error $PARENT1/logs/err.log --job-name STD_$SBID1"
    elif [ "$MODE" = "INVERT" ]; then
        SBATCHARGS="--exclude=nid00[2024-2055],nid00[2792-2823] --time 12:00:00 --ntasks 100 --ntasks-per-node 20 --no-requeue --output $PARENT1/logs/out_inverted.log --error $PARENT1/logs/err_inverted.log --job-name INV_$SBID1"
    elif [ "$MODE" = "MASK" ]; then
        SBATCHARGS="--exclude=nid00[2024-2055],nid00[2792-2823] --time 12:00:00 --ntasks 100 --ntasks-per-node 20 --no-requeue --output $PARENT1/logs/out_masked.log --error $PARENT1/logs/err_masked.log --job-name MSK_$SBID1"
    elif [ "$MODE" = "INVMASK" ]; then
        SBATCHARGS="--exclude=nid00[2024-2055],nid00[2792-2823] --time 12:00:00 --ntasks 100 --ntasks-per-node 20 --no-requeue --output $PARENT1/logs/out_inv_masked.log --error $PARENT1/logs/err_inv_masked.log --job-name INVMSK_$SBID1"
    fi

    jid1=$(sbatch $SBATCHARGS $FINDER/slurm_run_flashfinder.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1 $MODE)
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted $MODE job $j1"
    echo "$j1 = sbid $SBID1" >> jobs_to_sbids.txt
done
exit 0


