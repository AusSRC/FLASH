
#!/bin/bash

#######################################################################################################
# Edit these for the specific hpc-platform user:
CASDA_EMAIL="user@email"
CASDA_PWD="password_at_CASDA"
source $HOME/setonix_set_local_env.sh

# Local directories:
CRONDIR="/home/$USER/src/cronjobs"
DBDIR="/home/$USER/src/database"
PLOTDIR="/home/$USER/src/spectral_plot"

# Tmp directory for tarring etc - needs to be large capacity
TMPDIR="/scratch/ja3/$USER/tmp"
#######################################################################################################

IFS=","

# Config file to use for all the sbids
CONFIGFILE="./config.py"

# The parent directory holding the SBIDS
echo "parent = $DATA"

cd $DBDIR

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
SBIDARRAY=()
read -a SBIDARRAY <<< "$SBIDS"

for i in "${!SBIDARRAY[@]}"; do
    SBID="${SBIDARRAY[$i]}"
    python3.9 $FLASHDB/db_utils.py -m CATALOGUE -s $SBID -e $CASDA_EMAIL -p $CASDA_PWD -r -d $DATA
done
echo "downloaded: $SBIDS from CASDA"


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
        jid1=$(/bin/bash $SPECTRAL/run_container_spectral.sh $DATA "$SBID" $DATA/$SBID/$CONFIG)
        j1=$(echo $jid1 | awk '{print $4}')
        echo "Sumbitted job $j1"
        echo "$j1 = sbid $SBID" >> jobs_to_sbids.txt
        cd $CRONDIR
	jid2=$(sbatch --dependency=afterok:$j1 tar_spectral_outputs.sh $SBID)
        j2=$(echo $jid2 | awk '{print $4}')
	jid3=$(sbatch --dependency=afterok:$j2 push_spectral_to_oracle.sh $SBID)
    fi
done
