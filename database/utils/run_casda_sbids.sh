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
SBIDARRAY=(45762)
#####################################################################################
########### DO NOT EDIT FURTHER #####################################################
#####################################################################################

SBIDSIZE=${#SBIDARRAY[@]}

#####################################################################################
#####################################################################################

source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh
mkdir -p logs

for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"
    CONFIG="${CONFIGARRAY[$i]}"
    OUT="${OUTDARRAY[$i]}"
    RESULT="${RESARRAY[$i]}"

    jid1=$(/bin/bash $FLASHDB/slurm_run_casda_sbids.sh $SBID $FLASHPASS)
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted job $j1"
done
    
