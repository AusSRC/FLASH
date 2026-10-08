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
#!/bin/bash

source ~/set_local_flash_env.sh

MODE=$1

SBIDARR=( "$@" )
SBIDARRAY=( "${SBIDARR[@]:1}" )

case "$MODE" in
    "STD")
        OUTDIR_NAME="outputs"
        TAR_NAME="linefinder.tar.gz"
        RUN_TYPE="DETECTION"
        COMMENT="Linefinder_run"
        ;;
    "INVERT")
        OUTDIR_NAME="inverted_outputs"
        TAR_NAME="inverted_linefinder.tar.gz"
        RUN_TYPE="INVERTED"
        COMMENT="Inverted_linefinder_run"
        ;;
    "MASK")
        OUTDIR_NAME="masked_outputs"
        TAR_NAME="masked_linefinder.tar.gz"
        RUN_TYPE="MASKED"
        COMMENT="masked_linefinder_run"
        ;;
    "INVMASK")
        OUTDIR_NAME="inv_masked_outputs"
        TAR_NAME="inv_masked_linefinder.tar.gz"
        RUN_TYPE="INVMASKED"
        COMMENT="inv_masked_linefinder_run"
        ;;
esac

# Execute the SBID loop
for SBID1 in "${SBIDARRAY[@]}"; do

    # Define the Workdir
    WORKDIR=$DATA/outputs_to_transfer/${SBID1}_${RUN_TYPE}
    echo "Working in $WORKDIR"

    # Cleanup any old existing WORKDIR files & folders
    echo "Cleaning up WORKDIR"
    rm -rf "$WORKDIR"
    rm -f "${WORKDIR}.tar.gz"
    rm -f "${WORKDIR}.sha256"
    rm -f "${WORKDIR}.complete"

    # Make the WORKDIR and sub directories if it doesnt exist
    echo "Making WORKDIR and sub folders"
    mkdir -p "$WORKDIR"
    mkdir -p "$WORKDIR/config"
    mkdir -p "$WORKDIR/logs"
    mkdir -p "$WORKDIR/$OUTDIR_NAME"

    # Copy in Config, logs and tarball
    echo "Copying Config to WORKDIR"
    cp -r "$DATA/$SBID1/config" "$WORKDIR/config"

    echo "Copying Logs to WORKDIR"
    cp -r "$DATA/$SBID1/logs" "$WORKDIR/logs/"

    echo "Copying Tar to WORKDIR"
    cp "$DATA/$SBID1/$TAR_NAME" "$WORKDIR/$OUTDIR_NAME/"

    # Untar the bundle so we dont need to untar and worry about names
    # etc on VM
    echo "Unbundling Tar in WORKDIR"
    tar -zxf \
    "$WORKDIR/$OUTDIR_NAME/$TAR_NAME" \
    -C "$WORKDIR/$OUTDIR_NAME"
    rm "$WORKDIR/$OUTDIR_NAME/$TAR_NAME"

    # Make the metadata.json
    echo "Making run metadata.json"
    printf '{
      "SBID": "%s",
      "QUALITY": "NOT_VALIDATED",
      "COMMENT": "%s",
      "RUN_TYPE": "%s"
    }
    ' \
    "$SBID1" \
    "$COMMENT" \
    "$RUN_TYPE" \
    > "$WORKDIR/metadata.json"

    # Zip up the workdir for transfer & delete unzipped version
    echo "Tarring whole WORKDIR"
    tar -czf "${WORKDIR}.tar.gz" -C \
        "$(dirname "$WORKDIR")" \
        "$(basename "$WORKDIR")" && rm -rf "$WORKDIR"

    # Create Checksum for Zipped workdir
    echo "Making checksum of tarred WORKDIR"
    sha256sum "${WORKDIR}.tar.gz" \
        > "${WORKDIR}.sha256"

    echo "Marking tarred WORKDIR as ready to copy to db"
    touch "${WORKDIR}.complete"

done
#exit 0