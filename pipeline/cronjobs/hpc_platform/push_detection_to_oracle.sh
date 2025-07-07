#!/bin/bash
##########################################################
# This script will scp the outputs of the linefinder processing
# for an SBID to the Flash VM on Oracle, where it will be uploaded to the
# database. WARNING - it will delete any previous data for this 
# SBID.
#########################################################
# Set the client platform details:
TMPDIR=/mnt/tmp
PARENTDIR=/mnt/casda
CLIENT="152.67.97.254"
ORACLE_KEY="~/.ssh/oracle_flash_vm.key"

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

    # set up directories on Oracle VM
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID1/outputs $1/logs $SBID1/config $TMPDIR/$SBID1*; mkdir -p $SBID1/config $SBID1/logs $SBID1/outputs;"
    # Copy data to Oracle
    scp -i $ORACLE_KEY $DATA/$SBID1/linefinder.tar.gz flash@$CLIENT:$PARENTDIR/$SBID1/outputs/
    scp -i $ORACLE_KEY $DATA/$SBID1/config/* flash@$CLIENT:$PARENTDIR/$SBID1/config/
    scp -i $ORACLE_KEY $DATA/$SBID1/logs/* flash@$CLIENT:$PARENTDIR/$SBID1/logs/
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID1/outputs; tar -zxvf linefinder.tar.gz; rm linefinder.tar.gz"
    # Start a db_upload session at Oracle
    ssh -i $ORACLE_KEY flash@$CLIENT "cd ~/src/FLASH/database; python3 db_upload.py -m DETECTION -s $SBID1 -t $TMPDIR -d $PARENTDIR -pw aussrc -cs config -C 'Linefinder_run'"

    # Stash the SLURM logs
    mv slurm-*.out $DATA/tmp/
done
exit 0
