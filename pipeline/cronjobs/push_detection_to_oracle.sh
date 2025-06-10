#!/bin/bash
##########################################################
# This script will scp the outputs of the linefinder processing
# for an SBID to the Flash VM on Oracle, where it will be uploaded to the
# database. WARNING - it will delete any previous data for this 
# SBID.
#########################################################

# $1 is the sbid
#
QUALITY=`cat "$DATA"/"$1"/data_quality.txt`
if [ -z "$QUALITY" ]; then
    QUALITY="NOT_VALIDATED"
fi
 
echo "Uploading $1 linefinder results via Oracle to database"

# Set the tmp dir on Oracle
TMPDIR=/mnt/db/data/tmp
# Set the data dir (parent to SBID dir) on Oracle
PARENTDIR=/mnt/db/data
# set up directories on Oracle VM
ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "cd /mnt/db/data; rm -R $1/outputs $1/logs $1/config $TMPDIR/$1*; mkdir -p $1/config $1/logs $1/outputs;"
# Copy data to Oracle
scp -i ~/.ssh/oracle_flash_vm.key $DATA/$1/$1_linefinder.tar.gz flash@152.67.97.254:$PARENTDIR/$1/outputs/
scp -i ~/.ssh/oracle_flash_vm.key $DATA/$1/config/* flash@152.67.97.254:/mnt/db/data/$1/config/
scp -i ~/.ssh/oracle_flash_vm.key $DATA/$1/logs/* flash@152.67.97.254:/mnt/db/data/$1/logs/
# Start a db_upload session at Oracle
ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "cd /mnt/db/data/$1/outputs; tar -zxvf $1_linefinder.tar.gz; rm $1_linefinder.tar.gz"
ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "cd ~/src/FLASH/database; python3 db_upload.py -m DETECTION -s $1 -t $TMPDIR -d $PARENTDIR -pw aussrc -cs config -C 'Linefinder_run'"

# Stash the SLURM logs
mv slurm-*.out $DATA/tmp/
exit 0
