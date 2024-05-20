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
# The type of upload:
UPLOAD="SPECTRAL_PLOTS"

# The SBIDS to process - leave as () for auto checking of the parent directory:
#SBIDARRAY=(45754 45756 50000 50002 50003)
SBIDARRAY=()

# The parent directory holding the SBIDS
PARENTDIR="/scratch/ja3/ger063/data/casda"

# config directories used (relative to SBID directory)
CONFIGARRAY=("config")

#####################################################################################
########### DO NOT EDIT FURTHER #####################################################
#####################################################################################

# If the SBIDARRAY is not declared, then do an automatic check of the parent dir for sbid directories - sbid directory names should be a number only eg 45756
if [[ -z "${SBIDARRAY[@]}" ]]; then
    re='^[0-9]+$'
    cwd=$(pwd)
    cd $PARENTDIR
    set -- */
    ARR1="$@"
    ARR2=$(echo $ARR1 | tr "/ " "\n")
    for id in $ARR2
    do
        if [[ $id =~ $re ]]; then
            logname=$(ls -tp "$id/logs" | grep -v /$ | head -1)
            logfile="$id/logs/$logname"
            tag=$( tail -n 1 $logfile ) # Check the logfile to see if the job completed
            if [[ $tag =~ "Job took" ]]; then
                echo "Completed - adding $id to upload list"
                SBIDARRAY+=($id)
            else
                echo "Job not complete - $id not added"
            fi
        fi
    done
    cd $cwd
fi

SBIDSIZE=${#SBIDARRAY[@]}

for (( i=1; i<$SBIDSIZE; i++ ))
do
    CONFIGARRAY+=("config")
done

#####################################################################################
#####################################################################################

source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh

for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"
    CONFIG="${CONFIGARRAY[$i]}"
    OUT="${OUTDARRAY[$i]}"
    RESULT="${RESARRAY[$i]}"

    jid1=$(/bin/bash $FLASHDB/slurm_comp_db_upload.sh $SBID $PARENTDIR $FLASHPASS)
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted job $j1"
done
    
