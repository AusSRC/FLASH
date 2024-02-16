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

#####################################################################################
#####################################################################################
# The type of upload:
UPLOAD="SPECTRAL_PLOTS"
#UPLOAD="LINEFINDER"

# The tag to give the data: eg "FLASH Survey 1", or "FLASH Pilot2" etc
TAG="FLASH Survey 1"

# The SBIDS to process:
SBIDARRAY=(55247 55328 55394 55398 55399 55400 55420 55460 55464)
SBIDSIZE=${#SBIDARRAY[@]}

# The parent directory holding the SBIDS
PARENTDIR="/scratch/ja3/ger063/data/casda"

# Tmp directory for tarring etc - needs to be large capacity
TMPDIR="/scratch/ja3/ger063/tmp"

# Compute resource used
PLATFORM="setonix@pawsey"

# Comment to add (no spaces!)
COMMENT="reload after CASDA outage"

# config directories used (relative to SBID directory)
CONFIGARRAY=("config")
for (( i=1; i<$SBIDSIZE; i++ ))
do
    CONFIGARRAY+=("config")
done

###### The following are for linefinder uploads only ###############################
# linefinder output dirs used (relative to SBID dir)
OUTDARRAY=("outputs")
for (( i=1; i<$SBIDSIZE; i++ ))
do
    OUTDARRAY+=("outputs")
done

# linfinder results files created (relative to SBID dir)
RESARRAY=("outputs/results.dat")
for (( i=1; i<$SBIDSIZE; i++ ))
do
    RESARRAY+=("outputs/results.dat")
done

#####################################################################################
########### DO NOT EDIT FURTHER #####################################################
#####################################################################################

source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh

for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"
    CONFIG="${CONFIGARRAY[$i]}"
    OUT="${OUTDARRAY[$i]}"
    RESULT="${RESARRAY[$i]}"

    if [ "$UPLOAD" == "LINEFINDER" ]; then
        jid1=$(/bin/bash $FLASHDB/slurm_linefinder_db_upload.sh $SBID $CONFIG $OUT $RESULT $PARENTDIR $PLATFORM $COMMENT)
    elif [ "$UPLOAD" == "SPECTRAL_PLOTS" ]; then
        jid1=$(/bin/bash $FLASHDB/slurm_plot_db_upload.sh $SBID "$TAG" $TMPDIR $CONFIG $PARENTDIR $PLATFORM $COMMENT)
    fi
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted job $j1"
done
    
