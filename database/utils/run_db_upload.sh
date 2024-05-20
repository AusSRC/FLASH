
#!/bin/bash
######################################################################################
######################################################################################
#
#       Run uploads of spectral/linefinder outputs to FLASH database
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
#UPLOAD="LINEFINDER"

# The tag to give the data: eg "FLASH Survey 1", or "FLASH Pilot2" etc
TAG="FLASH Survey 1"

# The SBIDS to process - leave as () for auto checking of the parent directory:
SBIDARRAY=(60047 60093)
SBIDARRAY=(60094)
# The parent directory holding the SBIDS
PARENTDIR="/scratch/ja3/ger063/data/casda"

# Tmp directory for tarring etc - needs to be large capacity
TMPDIR="/scratch/ja3/ger063/tmp"

# Compute resource used
PLATFORM="setonix@pawsey"

# Comment to add (no spaces!)
COMMENT="CASDA_update"

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
#####################################################################################

source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh

for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"
    CONFIG="${CONFIGARRAY[$i]}"
    OUT="${OUTDARRAY[$i]}"
    RESULT="${RESARRAY[$i]}"

    if [ "$UPLOAD" == "LINEFINDER" ]; then
        jid1=$(/bin/bash $FLASHDB/slurm_linefinder_db_upload.sh $SBID $CONFIG $OUT $RESULT $PARENTDIR $PLATFORM $COMMENT $FLASHPASS)
    elif [ "$UPLOAD" == "SPECTRAL_PLOTS" ]; then
        jid1=$(/bin/bash $FLASHDB/slurm_plot_db_upload.sh $SBID "$TAG" $TMPDIR $CONFIG $PARENTDIR $PLATFORM $COMMENT $FLASHPASS)
    fi
    # Report
    j1=$(echo $jid1 | awk '{print $4}')
    echo "Sumbitted job $j1"
done
