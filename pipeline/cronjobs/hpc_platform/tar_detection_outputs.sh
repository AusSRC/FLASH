#!/bin/bash
###############################################################
# This script will tar up the linefinder outputs directory of a given SBID
# ############################################################
# $1 is the mode - STD, INVERT MASK or INVMASK
MODE=$1
# rest of $@ is the sbid(s) to process
SBIDARR=( "$@" )
SBIDARRAY=( ${SBIDARR[@]:1} )

# Map variables for the selected MODE (MODE doesn't change per SBID)
case "$MODE" in
    "STD")
        MSG_DESC="standard"
        OUTDIR_NAME="outputs"
        LOG_NAME="out.log"
        TAR_NAME="linefinder.tar.gz"
        ;;
    "INVERT")
        MSG_DESC="inverted "
        OUTDIR_NAME="inverted_outputs"
        LOG_NAME="out_inverted.log"
        TAR_NAME="inverted_linefinder.tar.gz"
        ;;
    "MASK")
        MSG_DESC="masked "
        OUTDIR_NAME="masked_outputs"
        LOG_NAME="out_masked.log"
        TAR_NAME="masked_linefinder.tar.gz"
        ;;
    "INVMASK")
        MSG_DESC="inverted masked "
        OUTDIR_NAME="inv_masked_outputs"
        LOG_NAME="out_inv_masked.log"
        TAR_NAME="inv_masked_linefinder.tar.gz"
        ;;
    *)
        echo "ERROR: Unknown MODE '$MODE'. Expected STD, INVERT, MASK, or INVMASK."
        exit 1
        ;;
esac


for SBID1 in "${SBIDARRAY[@]}"; do
    # Find how many sources were processed and add to log file
    INDIR="$DATA/$SBID1/spectra_ascii"
    OUTDIR="$DATA/$SBID1/$OUTDIR_NAME"
    LOGFILE="$DATA/$SBID1/logs/$LOG_NAME"
    
    INPUT_COUNT=$(find "$INDIR" -maxdepth 1 -type f -name "*opd.dat" 2>/dev/null | wc -l)
    PROCESSED_COUNT=$(find "$OUTDIR" -maxdepth 1 -type f -name "*resume.dat" 2>/dev/null | wc -l)
    
    echo "Found $INPUT_COUNT ascii files " >> "$LOGFILE"
    echo "Found $PROCESSED_COUNT output files " >> "$LOGFILE"

    echo "Tarring $SBID1 ${MSG_DESC} linefinder results"
    cd $DATA/$SBID1/$OUTDIR_NAME

    # Some runs do not have output pdf files; this way of calling tar ensures it doesn't fail if certain files are not found:
    # Enable nullglob
    shopt -s nullglob
    FILES=(results* *stats.dat *.pdf)

    if [ ${#FILES[@]} -gt 0 ]; then
        # Create the tarball in the parent directory
        tar -zcvf ../"$TAR_NAME" "${FILES[@]}"
        
        shopt -u nullglob

        # Force Lustre to flush I/O buffers so the file is fully written before we read it
        sync

        echo "Verifying local integrity of $TAR_NAME (this may take a long time for large files)..."
        
        if ! tar -tzf ../"$TAR_NAME"; then
            echo "ERROR: Local tarball $TAR_NAME is invalid or corrupted. Exiting."
            rm -f ../"$TAR_NAME"
            exit 1
        else
            echo "$TAR_NAME verification complete and ok!"
        fi
    else
        echo "Warning: No files found to archive for $TAR_NAME"
        shopt -u nullglob
    fi


done
exit 0
    
