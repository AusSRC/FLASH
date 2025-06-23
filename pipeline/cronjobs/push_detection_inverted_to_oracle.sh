#!/bin/bash
##########################################################
# This script will scp the outputs of the linefinder processing
# for an SBID to the Flash VM on Oracle, where it will be uploaded to the
# database. WARNING - it will delete any previous data for this 
# SBID.
#########################################################

# $@ is the sbid(s) to process
SBIDARRAY=( "$@" )

echo "Processing ${SBIDARRAY[@]}"

for SBID1 in "${SBIDARRAY[@]}"; do
    QUALITY=`cat "$DATA"/"$SBID1"/data_quality.txt`
    if [ -z "$QUALITY" ]; then
        QUALITY="NOT_VALIDATED"
    fi
     
    echo "Uploading $SBID1 linefinder results via Oracle to database"

    # Set the tmp dir on Oracle
    TMPDIR=/mnt/db/data/tmp
    # Set the data dir (parent to SBID dir) on Oracle
    PARENTDIR=/mnt/db/data
    # set up directories on Oracle VM
    ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "cd /mnt/db/data; rm -R $SBID1/inverted_outputs $1/logs $SBID1/config $TMPDIR/$SBID1*; mkdir -p $SBID1/config $SBID1/logs $SBID1/inverted_outputs;"
    # Copy data to Oracle
    scp -i ~/.ssh/oracle_flash_vm.key $DATA/$SBID1/inverted_linefinder.tar.gz flash@152.67.97.254:$PARENTDIR/$SBID1/inverted_outputs/
    scp -i ~/.ssh/oracle_flash_vm.key $DATA/$SBID1/config/* flash@152.67.97.254:/mnt/db/data/$SBID1/config/
    scp -i ~/.ssh/oracle_flash_vm.key $DATA/$SBID1/logs/* flash@152.67.97.254:/mnt/db/data/$SBID1/logs/
    # Start a db_upload session at Oracle
    ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "cd /mnt/db/data/$SBID1/inverted_outputs; tar -zxvf inverted_linefinder.tar.gz; rm inverted_linefinder.tar.gz"
    ssh -i ~/.ssh/oracle_flash_vm.key flash@152.67.97.254 "cd ~/src/FLASH/database; python3 db_upload.py -m INVERTED -s $SBID1 -t $TMPDIR -d $PARENTDIR -pw aussrc -cs config -o inverted_outputs -C 'Inverted_linefinder_run'"

    # Stash the SLURM logs
    mv slurm-*.out $DATA/tmp/
done
exit 0
