#!/bin/bash
##########################################################
# This script will scp the outputs of the spectral processing
# for an SBID to the Flash VM on Oracle, where it will be uploaded to the
# database. WARNING - it will delete any previous data for this 
# SBID.
#########################################################
# Set the client platform details:
TMPDIR=/mnt/tmp
PARENTDIR=/mnt/casda
CLIENT="152.67.97.254"
ORACLE_KEY="~/.ssh/oracle_flash_vm.key"
FLASHPASS="aussrc"
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
    scp -i $ORACLE_KEY $DATA/$SBID/config/* flash@$CLIENT:$PARENTDIR/$SBID/config/
    scp -i $ORACLE_KEY $DATA/$SBID/logs/plot_err*.log flash@$CLIENT:$PARENTDIR/$SBID/logs/err.log
    scp -i $ORACLE_KEY $DATA/$SBID/logs/plot_out*.log flash@$CLIENT:$PARENTDIR/$SBID/logs/out.log
    scp -i $ORACLE_KEY $DATA/catalogues/*$SBID*.xml flash@$CLIENT:$PARENTDIR/catalogues/
    scp -i $ORACLE_KEY $DATA/$SBID/*Spectra-image*.tar flash@$CLIENT:$PARENTDIR/$SBID/
    scp -i $ORACLE_KEY $DATA/$SBID/*sources_tarball.tar.gz flash@$CLIENT:$PARENTDIR/$SBID/SourceSpectra/
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID/spectra_plots; tar -zxvf *plots_tarball.tar.gz; rm *plots_tarball.tar.gz"
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID/SourceSpectra; tar -zxvf *sources_tarball.tar.gz; rm *sources_tarball.tar.gz"
    ssh -i $ORACLE_KEY flash@$CLIENT "source ~/set_local_flash_env.sh; cd ~/src/FLASH/database; python3 db_upload.py -m SPECTRAL -q $QUALITY -s $SBID -t $TMPDIR -d $PARENTDIR -pw $FLASHPASS -cs config -C 'CASDA_upload' >> $PARENTDIR/$SBID1/'$SBID1'_spectral_db.log 2>&1"

done

# Stash the SLURM logs
mv slurm-*.out $DATA/tmp/
exit 0
