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
# The SBIDS to process:
SBIDARRAY=(55464 55460 55420 55400 55399 55398 55394 55328 55247)
SBIDSIZE=${#SBIDARRAY[@]}

# Config file to use for all the sbids
CONFIGFILE="./config.py"

# The parent directory holding the SBIDS
PARENT_DIR="/scratch/ja3/ger063/data/casda"

######################################################################################
######################################################################################

# config directories used (relative to each SBID directory)
CONFIGARRAY=("config")
for (( i=1; i<$SBIDSIZE; i++ ))
do
    CONFIGARRAY+=("config")
done


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

