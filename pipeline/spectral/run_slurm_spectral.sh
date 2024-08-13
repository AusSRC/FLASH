#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_slurm_spectral.sh", which calls:
#                   2) "run_container_spectral.sh", which calls:
#                       3) a singularity container running "run_spectrals.sh"
#
######################################################################################
######################################################################################
# The SBIDS to process - leave as () for auto checking of the parent directory:
#SBIDARRAY=(50019 51443 45833 45828 51444 45815 50022 45823 50021 51441 51440 45762 45835 51015 45825 51442)
SBIDARRAY=()

# Config file to use for all the sbids
CONFIGFILE="./config.py"

# The parent directory holding the SBIDS
PARENT_DIR="/scratch/ja3/ger063/data/casda"

# config directories used (relative to each SBID directory)
CONFIGARRAY=("config")

######################################################################################
########### DO NOT EDIT FURTHER #####################################################
######################################################################################
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
            SBIDARRAY+=($id)
        fi
    done
    cd $cwd
fi

SBIDSIZE=${#SBIDARRAY[@]}
for (( i=1; i<$SBIDSIZE; i++ ))
do
    CONFIGARRAY+=("config")
done

echo "Starting jobs ${SBIDARRAY[@]}" > jobs_to_sbids.txt

for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"
    CONFIG="${CONFIGARRAY[$i]}"
 
    # pass to container script: 
    #   1) parent input data directory (holds the sbid, noise, catalogues subdirectories)
    #   2) string of sbids to process
    #   3) plot_spectral config directory (holds config.py)
    mkdir -p $PARENT_DIR/$SBID/$CONFIG
    cp $CONFIGFILE $PARENT_DIR/$SBID/$CONFIG
    jid1=$(/bin/bash ./run_container_spectral.sh $PARENT_DIR "$SBID" $PARENT_DIR/$SBID/$CONFIG)
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted job $j1"
    echo "$j1 = sbid $SBID" >> jobs_to_sbids.txt

done

