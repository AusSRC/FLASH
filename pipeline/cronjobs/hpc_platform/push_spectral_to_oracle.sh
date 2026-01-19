#!/bin/bash
##########################################################
# This script will scp the outputs of the spectral processing
# for an SBID to the Flash VM on Oracle, where it will be uploaded to the
# database. WARNING - it will delete any previous data for this 
# SBID.
#########################################################
source ~/set_local_flash_env.sh
# Set the client platform details:
COMMENT="new_CASDA_data"
#COMMENT="update_missing_plots"
TMPDIR=$CLIENTTMP
PARENTDIR=$CLIENTDATA
CLIENT=$CLIENTIP
ORACLE_KEY=$CLIENTKEY
#########################################################
# $@ is the sbid(s) to process
SBIDARRAY=( "$@" )

# $SBID is the sbid
for SBID in "${SBIDARRAY[@]}"; do

    QUALITY=`cat "$DATA"/"$SBID"/data_quality.txt`
    if [ -z "$QUALITY" ]; then
        QUALITY="NOT_VALIDATED"
    fi
     
    echo "Uploading $SBID spectral plot results via Oracle to database"

    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID/spectra_ascii* $SBID/spectra_plots* $TMPDIR/$SBID* $SBID/logs; mkdir -p $SBID/config $SBID/spectra_plots $SBID/spectra_ascii $SBID/SourceSpectra $SBID/logs;"
    scp -i $ORACLE_KEY $DATA/$SBID/*ascii_tarball.tar.gz flash@$CLIENT:$TMPDIR
    scp -i $ORACLE_KEY $DATA/$SBID/*plots_tarball.tar.gz flash@$CLIENT:$PARENTDIR/$SBID/spectra_plots/

    # Compare the size of the plot tarball with the original
    LOCAL_SIZE=$(stat -c %s $DATA/$SBID/${SBID}_plots_tarball.tar.gz)
    REMOTE_SIZE=$(ssh -i $ORACLE_KEY flash@$CLIENT "stat -c %s $PARENTDIR/$SBID/spectra_plots/${SBID}_plots_tarball.tar.gz")
    if [ "$LOCAL_SIZE" -eq "$REMOTE_SIZE" ]; then
        echo ""
    else
        echo "❌ Failure: plot sizes for $SBID do not match."
        continue
    fi

    scp -i $ORACLE_KEY $DATA/$SBID/config/* flash@$CLIENT:$PARENTDIR/$SBID/config/
    ssh -i $ORACLE_KEY flash@$CLIENT "mkdir -p $PARENTDIR/$SBID/logs"
    cat $DATA/$SBID/logs/plot_err*.log | ssh -i $ORACLE_KEY flash@$CLIENT "cat > $PARENTDIR/$SBID/logs/err.log"
    cat $DATA/$SBID/logs/plot_out*.log | ssh -i $ORACLE_KEY flash@$CLIENT "cat > $PARENTDIR/$SBID/logs/out.log"
    scp -i $ORACLE_KEY $DATA/catalogues/*$SBID*.xml flash@$CLIENT:$PARENTDIR/catalogues/
    scp -i $ORACLE_KEY $DATA/$SBID/*Spectra-image*.tar flash@$CLIENT:$PARENTDIR/$SBID/
    scp -i $ORACLE_KEY $DATA/$SBID/*sources_tarball.tar.gz flash@$CLIENT:$PARENTDIR/$SBID/SourceSpectra/
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID/spectra_plots; tar -zxvf *plots_tarball.tar.gz"
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID/SourceSpectra; tar -zxvf *sources_tarball.tar.gz"
    echo "Starting upload to FLASH db"
    ssh -i $ORACLE_KEY flash@$CLIENT "source ~/set_local_flash_env.sh; cd ~/src/FLASH/database; python3 db_upload.py -m SPECTRAL -q $QUALITY -s $SBID -t $TMPDIR -d $PARENTDIR -pw $FLASHPASS -cs config -C $COMMENT >> $PARENTDIR/$SBID/'$SBID'_spectral_db.log 2>&1"

done
echo "Completed data upload to FLASH db for ${SBIDARRAY[@]}"

# Stash the SLURM logs
echo "Checking for old SLURM logs"
mv slurm-*.out $DATA/tmp/
exit 0
