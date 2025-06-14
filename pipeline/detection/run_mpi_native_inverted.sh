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
# The SBIDS to process (if not pass on the command line):

if [ $# -eq 0 ]
    then
        rm jobs_to_sbids.txt
        SBIDARRAY=(55247 55398 55460)
else
        SBIDARRAY=( "$@" )
fi
echo "${SBIDARRAY[@]}"


# The parent directory holding the SBIDS
PARENT_DIR="/scratch/ja3/ger063/data/casda"

# Directory to move bad data files to:
BAD_FILES_DIR="/scratch/ja3/ger063/data/casda/bad_ascii_files"


#####################################################################################
############### DO NOT EDIT FURTHER #################################################

source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh

for SBID1 in "${SBIDARRAY[@]}"; do
    PARENT1=$PARENT_DIR/$SBID1
    cp slurm_linefinder_inverted.ini model.txt $PARENT1/config
    # Check if a mask file exists:
    MASK="masks/SBID${SBID1}_mask.txt"
    if test -f $MASK; then
            cp $MASK "${PARENT1}/config/mask.txt"
    fi

     # pass to slurm_run scripts: 
    jid1=$(/bin/bash $FINDER/slurm_run_flashfinder_inverted.sh $PARENT1 spectra_ascii $BAD_FILES_DIR $SBID1)
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted job $j1"
    echo "$j1 = sbid $SBID1" >> jobs_to_sbids.txt
done
exit 0


