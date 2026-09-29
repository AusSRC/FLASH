#!/bin/bash
##########################################################
# GWHG, AusSRC Aug 2025
# This script will scp the outputs of the linefinder processing
# for an SBID to the Flash VM on client, where it will be uploaded to the
# database. WARNING - it will delete any previous data for this 
# SBID.
#
# GWHG Sep 2026
# The script will also determine, for each SBID, how many sources there were
# and how many were actually processed (as some may have been tagged as 'bad',
# you wouldn't generally expect the numbers to match.
#
#########################################################
source ~/set_local_flash_env.sh
# Set the client platform details:
TMPDIR=$CLIENTTMP
PARENTDIR=$CLIENTDATA
CLIENT=$CLIENTIP
ORACLE_KEY=$CLIENTKEY

#########################################################
# $1 is the mode - STD, INVERT MASK or INVMASK
MODE=$1
# rest of $@ is the sbid(s) to process
SBIDARR=( "$@" )
SBIDARRAY=( "${SBIDARR[@]:1}" )

echo "Processing ${SBIDARRAY[@]}"

# Map variables for the selected MODE (MODE doesn't change per SBID)
case "$MODE" in
    "STD")
        MSG_DESC=""
        OUTDIR_NAME="outputs"
        LOG_NAME="out.log"
        ERR_NAME="err.log"
        TAR_NAME="linefinder.tar.gz"
        DB_MODE="DETECTION"
        DB_LOG_SUFFIX="std_detection_db.log"
        DB_COMMENT="Linefinder_run"
        ;;
    "INVERT")
        MSG_DESC="inverted "
        OUTDIR_NAME="inverted_outputs"
        LOG_NAME="out_inverted.log"
        ERR_NAME="err_inverted.log"
        TAR_NAME="inverted_linefinder.tar.gz"
        DB_MODE="INVERTED"
        DB_LOG_SUFFIX="invert_detection_db.log"
        DB_COMMENT="Inverted_linefinder_run"
        ;;
    "MASK")
        MSG_DESC="masked "
        OUTDIR_NAME="masked_outputs"
        LOG_NAME="out_masked.log"
        ERR_NAME="err_masked.log"
        TAR_NAME="masked_linefinder.tar.gz"
        DB_MODE="MASKED"
        DB_LOG_SUFFIX="mask_detection_db.log"
        DB_COMMENT="masked_linefinder_run"
        ;;
    "INVMASK")
        MSG_DESC="inverted masked "
        OUTDIR_NAME="inv_masked_outputs"
        LOG_NAME="out_inv_masked.log"
        ERR_NAME="err_inv_masked.log"
        TAR_NAME="inv_masked_linefinder.tar.gz"
        DB_MODE="INVMASKED"
        DB_LOG_SUFFIX="inv_mask_detection_db.log"
        DB_COMMENT="inv_masked_linefinder_run"
        ;;
    *)
        echo "ERROR: Unknown MODE '$MODE'. Expected STD, INVERT, MASK, or INVMASK."
        exit 1
        ;;
esac

# Execute the SBID loop
for SBID1 in "${SBIDARRAY[@]}"; do
    INDIR="$DATA/$SBID1/spectra_ascii"
    echo "Uploading $SBID1 ${MSG_DESC}linefinder results via client to database"

    # Find how many sources were processed and add to log file
    OUTDIR="$DATA/$SBID1/$OUTDIR_NAME"
    LOGFILE="$DATA/$SBID1/logs/$LOG_NAME"
    
    INPUT_COUNT=$(find "$INDIR" -maxdepth 1 -type f -name "*opd.dat" 2>/dev/null | wc -l)
    PROCESSED_COUNT=$(find "$OUTDIR" -maxdepth 1 -type f -name "*resume.dat" 2>/dev/null | wc -l)
    
    echo "Found $INPUT_COUNT ascii files " >> "$LOGFILE"
    echo "Found $PROCESSED_COUNT output files " >> "$LOGFILE"

    # set up directories on client VM
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR; rm -R $SBID1/$OUTDIR_NAME $SBID1/logs $SBID1/config $TMPDIR/$SBID1* 2>/dev/null || true; mkdir -p $SBID1/config $SBID1/logs $SBID1/$OUTDIR_NAME;"
    
    # Copy data to client
    scp -i $ORACLE_KEY $DATA/$SBID1/$TAR_NAME flash@$CLIENT:$PARENTDIR/$SBID1/$OUTDIR_NAME/
    scp -i $ORACLE_KEY $DATA/$SBID1/config/* flash@$CLIENT:$PARENTDIR/$SBID1/config/
    scp -i $ORACLE_KEY $DATA/$SBID1/logs/* flash@$CLIENT:$PARENTDIR/$SBID1/logs/

    # Create checksum for output tarball and send to client
    cd $DATA/$SBID1/
    md5sum $TAR_NAME > ${SBID1}.md5 
    scp -i $ORACLE_KEY ${SBID1}.md5 flash@$CLIENT:$PARENTDIR/$SBID1/$OUTDIR_NAME/

    # Check checksum on client
    if ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID1/$OUTDIR_NAME/ && md5sum -c ${SBID1}.md5 --quiet"; then
        echo "Tarball checksum verified successfully."
    else
        echo "WARNING: Tarball checksum failed! Exiting"
        exit 1
    fi

    # Extract tarball and start a db_upload session at client
    ssh -i $ORACLE_KEY flash@$CLIENT "cd $PARENTDIR/$SBID1/$OUTDIR_NAME; tar -zxvf $TAR_NAME; rm $TAR_NAME"
    ssh -i $ORACLE_KEY flash@$CLIENT "source ~/set_local_flash_env.sh;cd ~/src/FLASH/database; python3 db_upload.py -m $DB_MODE -s $SBID1 -t $TMPDIR -d $PARENTDIR -pw $FLASHPASS -cs config -l $LOG_NAME -e $ERR_NAME -o $OUTDIR_NAME -C '$DB_COMMENT' >> $PARENTDIR/$SBID1/'$SBID1'_${DB_LOG_SUFFIX} 2>&1"

    # Stash the SLURM logs
    mv slurm-*.out $DATA/tmp/
done
exit 0

