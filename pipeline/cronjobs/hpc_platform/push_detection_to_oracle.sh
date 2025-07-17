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
# $1 is the mode - STD, INVERT or MASK
MODE=$1
# rest of $@ is the sbid(s) to process
SBIDARR=( "$@" )
SBIDARRAY=${SBIDARR[@]:1}

echo "Processing ${SBIDARRAY[@]}"

for SBID1 in "${SBIDARRAY[@]}"; do
    if [ "$MODE" = "STD" ]; then
        echo "Uploading $SBID1 linefinder results via Oracle to database"

        # set up directories on Oracle VM
        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID1/outputs $SBID1/logs $SBID1/config $TMPDIR/$SBID1*; mkdir -p $SBID1/config $SBID1/logs $SBID1/outputs;"
        # Copy data to Oracle
        scp -i $ORACLE_KEY $DATA/$SBID1/linefinder.tar.gz flash@$CLIENT:$PARENTDIR/$SBID1/outputs/
        scp -i $ORACLE_KEY $DATA/$SBID1/config/* flash@$CLIENT:$PARENTDIR/$SBID1/config/
        scp -i $ORACLE_KEY $DATA/$SBID1/logs/* flash@$CLIENT:$PARENTDIR/$SBID1/logs/
        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID1/outputs; tar -zxvf linefinder.tar.gz; rm linefinder.tar.gz"
        # Start a db_upload session at Oracle
        ssh -i $ORACLE_KEY flash@$CLIENT "cd ~/src/FLASH/database; python3 db_upload.py -m DETECTION -s $SBID1 -t $TMPDIR -d $PARENTDIR -pw aussrc -cs config -C 'Linefinder_run'"
    elif [ "$MODE" = "INVERT" ]
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
    elif [ "$MODE" = "MASK" ]
        echo "Uploading $SBID1 masked linefinder results via Oracle to database"

        # set up directories on Oracle VM
        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID1/masked_outputs $SBID1/logs $SBID1/config $TMPDIR/$SBID1*; mkdir -p $SBID1/config $SBID1/logs $SBID1/masked_outputs;"
        # Copy data to Oracle
        scp -i $ORACLE_KEY $DATA/$SBID1/masked_linefinder.tar.gz flash@$CLIENT:$PARENTDIR/$SBID1/masked_outputs/
        scp -i $ORACLE_KEY $DATA/$SBID1/config/* flash@$CLIENT:$PARENTDIR/$SBID1/config/
        scp -i $ORACLE_KEY $DATA/$SBID1/logs/* flash@$CLIENT:$PARENTDIR/$SBID1/logs/
        # Start a db_upload session at Oracle
        ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID1/masked_outputs; tar -zxvf masked_linefinder.tar.gz; rm masked_linefinder.tar.gz"
        ssh -i $ORACLE_KEY flash@$CLIENT "source ~/set_local_env.sh;cd ~/src/FLASH/database; python3 db_upload.py -m MASKED -s $SBID1 -t $TMPDIR -d $PARENTDIR -pw aussrc -cs config -l out_masked.log -e err_masked.log -o masked_outputs -C 'masked_linefinder_run'"

    fi

    # Stash the SLURM logs
    mv slurm-*.out $DATA/tmp/
done
exit 0
