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
    echo "Uploading $SBID1 inverted linefinder results via Oracle to database"

    # set up directories on Oracle VM
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID1/inverted_outputs $SBID1/logs $SBID1/config $TMPDIR/$SBID1*; mkdir -p $SBID1/config $SBID1/logs $SBID1/inverted_outputs;"
    # Copy data to Oracle
    scp -i $ORACLE_KEY $DATA/$SBID1/inverted_linefinder.tar.gz flash@$CLIENT:$PARENTDIR/$SBID1/inverted_outputs/
    scp -i $ORACLE_KEY $DATA/$SBID1/config/* flash@$CLIENT:$PARENTDIR/$SBID1/config/
    scp -i $ORACLE_KEY $DATA/$SBID1/logs/* flash@$CLIENT:$PARENTDIR/$SBID1/logs/
    # Start a db_upload session at Oracle
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID1/inverted_outputs; tar -zxvf inverted_linefinder.tar.gz; rm inverted_linefinder.tar.gz"
    ssh -i $ORACLE_KEY flash@$CLIENT "source ~/set_local_env.sh;cd ~/src/FLASH/database; python3 db_upload.py -m INVERTED -s $SBID1 -t $TMPDIR -d $PARENTDIR -pw aussrc -cs config -l out_inverted.log -e err_inverted.log -o inverted_outputs -C 'Inverted_linefinder_run'"

    # Stash the SLURM logs
    mv slurm-*.out $DATA/tmp/
done
exit 0
