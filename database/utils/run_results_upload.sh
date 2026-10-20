#!/bin/bash
######################################################################################
######################################################################################
#
#       Run uploads of linefinder outputs to FLASH database
#
#   NOTE:   The script calling order is:
#               1) "run_db_upload.sh", (this file) which calls:
#                   2) "slurm_run_db_upload.sh"
#
#       This requires the FLASHDB password to be passed on the command line eg:
#               ./run_db_upload.sh my_password

#####################################################################################
#####################################################################################
FLASHPASS=$1

# The SBIDS to process - leave as () for auto checking of the parent directory:
#SBIDARRAY=(45754 45756 50000 50002 50003)
SBIDARRAY=()

# The parent directory holding the SBIDS
PARENTDIR="/scratch/ja3/ger063/data/casda"

#####################################################################################
########### DO NOT EDIT FURTHER #####################################################
#####################################################################################

SBIDSIZE=${#SBIDARRAY[@]}

source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh

for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"

    jid1=$(/bin/bash $FLASHDB/slurm_result_db_upload.sh $SBID $PARENTDIR $FLASHPASS)
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted job $j1"
done
    
