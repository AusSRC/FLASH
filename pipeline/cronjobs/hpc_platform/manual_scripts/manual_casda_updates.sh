
#!/bin/bash

#######################################################################################################
# Edit these for the specific user:
CASDA_EMAIL="user@email"
CASDA_PWD="password_at_CASDA"
#######################################################################################################

FLASHPASS=$1

sbids="72751"
sbids="72378,72385,72386,72387,72388"
sbids="72398,72494,72495,72496,72507,72669,72670,72746"
sbids="72746,72751"

# Local directories:
CRONDIR="/home/$USER/src/cronjobs"
DBDIR="/home/$USER/src/database"
PLOTDIR="/home/$USER/src/spectral_plot"

# Tmp directory for tarring etc - needs to be large capacity
TMPDIR="/scratch/ja3/$USER/tmp"

# The tag to give the data: eg "FLASH Survey 1", or "FLASH Pilot2" etc
TAG="flash pilot 2"
TAG="FLASH Survey 1"

# Compute resource used
PLATFORM="setonix@pawsey"

# Comment to add (no spaces!)
COMMENT="CASDA_update"

# The parent directory holding the SBIDS
PARENTDIR="/scratch/ja3/ger063/data/casda"

# Config file to use for all the sbids
CONFIGFILE="./config.py"

# The parent directory holding the SBIDS
PARENT_DIR=$DATA

source ~/setonix_set_local_env.sh
cd $DBDIR

# Query CASDA for new sbids
python3.9 $FLASHDB/db_utils.py -m CATALOGUE -s $sbids -e $CASDA_EMAIL -p $CASDA_PWD -pw $FLASHPASS -r

echo "Finished CASDA downloads"
SBIDS=$(sed "s/,/ /g" <<< $sbids)
IFS=" "
SBIDARRAY=()
read -a SBIDARRAY <<< "$SBIDS"
echo "downloaded: $SBIDS"

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
    if [ -d "$PARENTDIR/$SBID/SourceSpectra" ]
    then
        
        cd $PLOTDIR
        # pass to container script:
        #   1) parent input data directory (holds the sbid, noise, catalogues subdirectories)
        #   2) string of sbids to process
        #   3) plot_spectral config directory (holds config.py)
        mkdir -p $PARENTDIR/$SBID/$CONFIG
        cp $CONFIGFILE $PARENTDIR/$SBID/$CONFIG
        jid1=$(/bin/bash ./run_container_spectral.sh $PARENTDIR "$SBID" $PARENT_DIR/$SBID/$CONFIG)
        j1=$(echo $jid1 | awk '{print $4}')
        echo "Sumbitted job $j1"
        echo "$j1 = sbid $SBID" >> jobs_to_sbids.txt
        cd $CRONDIR
	jid2=$(sbatch --dependency=afterok:$j1 tar_spectral_outputs.sh $SBID)
        j2=$(echo $jid2 | awk '{print $4}')
	jid3=$(sbatch --dependency=afterok:$j2 push_spectral_to_oracle.sh $SBID)
    fi
done
