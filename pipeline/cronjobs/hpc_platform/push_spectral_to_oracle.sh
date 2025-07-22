#!/bin/bash
##########################################################
# This script will scp the outputs of the spectral processing
# for an SBID to the Flash VM on Oracle, where it will be uploaded to the
# database. WARNING - it will delete any previous data for this 
# SBID.
#########################################################
# Set the tmp dir on the client
TMPDIR=/mnt/tmp
# Set the data dir (parent to SBID dir) on the client
PARENTDIR=/mnt/casda

# $1 is the sbid
#
QUALITY=`cat "$DATA"/"$1"/data_quality.txt`
if [ -z "$QUALITY" ]; then
    QUALITY="NOT_VALIDATED"
fi
 
echo "Uploading $1 spectral plot results via Oracle to database"

ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "cd $PARENTDIR; rm -R $1/spectra_ascii* $1/spectra_plots* $TMPDIR/$1*; mkdir -p $1/config $1/spectra_plots $1/spectra_ascii $1/SourceSpectra;"
scp -i ~/.ssh/oracle_flash_vm.key $DATA/$1/*ascii_tarball.tar.gz flash@152.67.97.254:$TMPDIR
scp -i ~/.ssh/oracle_flash_vm.key $DATA/$1/*plots_tarball.tar.gz flash@152.67.97.254:$PARENTDIR/$1/spectra_plots/
scp -i ~/.ssh/oracle_flash_vm.key $DATA/$1/config/* flash@152.67.97.254:$PARENTDIR/$1/config/
scp -i ~/.ssh/oracle_flash_vm.key $DATA/catalogues/*$1*.xml flash@152.67.97.254:$PARENTDIR/catalogues/
scp -i ~/.ssh/oracle_flash_vm.key $DATA/$1/*Spectra-image*.tar flash@152.67.97.254:$PARENTDIR/$1/
scp -i ~/.ssh/oracle_flash_vm.key $DATA/$1/*sources_tarball.tar.gz flash@152.67.97.254:$PARENTDIR/$1/SourceSpectra/
ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "cd $PARENTDIR/$1/spectra_plots; tar -zxvf *plots_tarball.tar.gz; rm *plots_tarball.tar.gz"
ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "cd $PARENTDIR/$1/SourceSpectra; tar -zxvf *sources_tarball.tar.gz; rm *sources_tarball.tar.gz"
ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "source ~/set_local_flash_env.sh; cd ~/src/FLASH/database; python3 db_upload.py -m SPECTRAL -q $QUALITY -s $1 -t $TMPDIR -d $PARENTDIR -pw aussrc -cs config -C 'CASDA_upload'"

# Stash the SLURM logs
mv slurm-*.out $DATA/tmp/
exit 0
