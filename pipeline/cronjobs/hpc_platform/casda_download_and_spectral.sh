
#!/bin/bash

#######################################################################################################
source $HOME/set_local_flash_env.sh

# Local directories:
CRONDIR="/home/$USER/src/cronjobs"
DBDIR="/home/$USER/src/database"
PLOTDIR="/home/$USER/src/spectral_plot"

# Tmp directory for tarring etc - needs to be large capacity
TMPDIR="/scratch/ja3/$USER/tmp"
#######################################################################################################
source /software/projects/ja3/ger063/setonix/python/bin/activate
IFS=","

SBIDARR=()
SBIDARRAY=()

# Config file to use for all the sbids
CONFIGFILE="./config.py"

# The parent directory holding the SBIDS
echo "parent = $DATA"

cd $DBDIR

# Check if we were passed sbids on the command line:
if [ "$#" -gt 0 ]; then
    SBIDARR=( "$@" )
else
# If not, check the log sent over from the client
    output=$( tail -n 1 $CRONDIR/new_sbids.log)
    sbids=${output:1: -1}
    if test "$output" == "[]"
    then
        echo "No sbids to process"
        exit
    fi

    sbids=$(sed "s/ //g" <<< $sbids)
    sbids="${sbids//\'}"
    SBIDS=$(sed "s/,/ /g" <<< $sbids)

    IFS=" "
    read -a SBIDARR <<< "$SBIDS"
fi

# Sort the array in ascending numerical order:
readarray -td '' sorted_array < <(printf '%s\0' "${SBIDARR[@]}" | sort -z -n)

# Limit size of SBIDARRAY to 10:
SBIDARRAY=( "${sorted_array[@]:0:10}" )

echo "To download: ${SBIDARRAY[@]} from CASDA"
for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"
    python3.9 $FLASHDB/db_utils.py -m CATALOGUE -s $SBID -e $CASDA_EMAIL -p $CASDA_PWD -r -d $DATA
done
echo "downloaded: ${SBIDARRAY[@]} from CASDA"


# Process the sbids
cd $PLOTDIR
echo "Submitting spectral plot jobs:"
echo


# config directories used (relative to each SBID directory)
CONFIGARRAY=("config")
SBIDSIZE=${#SBIDARRAY[@]}
for (( i=1; i<$SBIDSIZE; i++ ))
do
    CONFIGARRAY+=("config")
done

for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"
    CONFIG="${CONFIGARRAY[$i]}"

    if [ -d "$DATA/$SBID/SourceSpectra" ]
    then
        cd $PLOTDIR
        # pass to container script:
        #   1) parent input data directory (holds the sbid, noise, catalogues subdirectories)
        #   2) string of sbids to process
        #   3) plot_spectral config directory (holds config.py)
        mkdir -p $DATA/$SBID/$CONFIG
        cp $CONFIGFILE $DATA/$SBID/$CONFIG
        jid1=$(/bin/bash $FLASHHOME/pipeline/spectral/run_container_spectral.sh $DATA "$SBID" $DATA/$SBID/$CONFIG)
        j1=$(echo $jid1 | awk '{print $4}')
        echo "Sumbitted job $j1"
        echo "$j1 = sbid $SBID" >> jobs_to_sbids.txt
        cd $CRONDIR
	jid2=$(sbatch --dependency=afterok:$j1 tar_spectral_outputs.sh $SBID)
        j2=$(echo $jid2 | awk '{print $4}')
	jid3=$(sbatch --dependency=afterok:$j2 push_spectral_to_oracle.sh $SBID)
    fi
done
