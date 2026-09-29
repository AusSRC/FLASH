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
        TAR_NAME="linefinder.tar.gz"
        ;;
    "INVERT")
        MSG_DESC="inverted "
        OUTDIR_NAME="inverted_outputs"
        TAR_NAME="inverted_linefinder.tar.gz"
        ;;
    "MASK")
        MSG_DESC="masked "
        OUTDIR_NAME="masked_outputs"
        TAR_NAME="masked_linefinder.tar.gz"
        ;;
    "INVMASK")
        MSG_DESC="inverted masked "
        OUTDIR_NAME="inv_masked_outputs"
        TAR_NAME="inv_masked_linefinder.tar.gz"
        ;;
    *)
        echo "ERROR: Unknown MODE '$MODE'. Expected STD, INVERT, MASK, or INVMASK."
        exit 1
        ;;
esac


for SBID1 in "${SBIDARRAY[@]}"; do
    echo "Tarring $SBID1 ${MSG_DESC} linefinder results"
    cd $DATA/$SBID1/$OUTDIR_NAME; tar -zcvf $TAR_NAME results* *stats.dat *.pdf; mv $TAR_NAME ../
    echo "Verifying local integrity of $TAR_NAME..."
    if ! tar -tzf ../"$TAR_NAME" >/dev/null 2>&1; then
        echo "ERROR: Local tarball $TAR_NAME is invalid or corrupted on HPC platform. Exiting."
        rm $tar_file
	# if one fails, then we exit the whole process, so no dependencies will be run.
        exit 1
    else
	echo "$TAR_NAME ok!"
    fi

done
exit 0
