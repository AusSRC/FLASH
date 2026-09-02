#!/bin/bash
##########################################################
# This script will bundle everything to do with the run into a single
# transferable tar zip and completion file which the VM will poll for
#########################################################
source ~/set_local_flash_env.sh

# Set the details for this runs meta data file:
COMMENT="new_CASDA_data"
RUN_TYPE="SPECTRAL"

#########################################################
# $@ is the sbid(s) to process
SBIDARRAY=( "$@" )

# $SBID is the sbid
for SBID in "${SBIDARRAY[@]}"; do

    # Bundle everything into one folder & zip it. Note we aim here to put
    # everything under SBID_TYPE in the structure expected by the uploader,
    # but some parts like the ascii_tarball & catalogs need to go different
    # places on the VM than the rest (tmp & catalogs rather than SBID),
    # they are bundled here for convenience in the polled fetch

    # Define where we will be working
    WORKDIR=$DATA/outputs_to_transfer/$SBID\_$RUN_TYPE

    # If we are working in this folder, ensure the folder for it and especially
    # the complete mark for it is not present
    echo "Removing old ${WORKDIR} and its complete flag in staging area"
    rm -f $WORKDIR
    rm -f "$(dirname "$WORKDIR")/$(basename "$WORKDIR").complete"

    # Make the needed folders & everything down to them
    echo "Making ${WORKDIR} in staging area"
    mkdir -p $WORKDIR/SourceSpectra
    mkdir -p $WORKDIR/spectra_plots
    mkdir -p $WORKDIR/catalogues
    mkdir -p $WORKDIR/logs

    # Copy all data into our working dir
    echo "Copying config to staging area"
    cp -r $DATA/$SBID/config $WORKDIR/config

    echo "Copying logs to staging area"
    cat "$DATA/$SBID"/logs/plot_err*.log > "$WORKDIR/logs/err.log"
    cat "$DATA/$SBID"/logs/plot_out*.log > "$WORKDIR/logs/out.log"

    echo "Copying catalogues to staging area"
    cp $DATA/catalogues/*$SBID*.xml $WORKDIR/catalogues/

    echo "Copying tarballs to staging area"
    cp $DATA/$SBID/*ascii_tarball.tar.gz $WORKDIR/
    cp $DATA/$SBID/*Spectra-image*.tar $WORKDIR/
    cp $DATA/$SBID/*sources_tarball.tar.gz $WORKDIR/SourceSpectra/
    cp $DATA/$SBID/*plots_tarball.tar.gz $WORKDIR/spectra_plots/

    # Untar the tars that are expected to be folders for uploader
    echo "Untarring sources_tarball and plots_tarball "
    tar -zxf "$WORKDIR/SourceSpectra/"*sources_tarball.tar.gz -C "$WORKDIR/SourceSpectra"
    tar -zxf "$WORKDIR/spectra_plots/"*plots_tarball.tar.gz -C "$WORKDIR/spectra_plots"

    # Construct the meta data file that will be used by data uploader on VM
    # to populate args.
    echo "Creating Metadata file in staging area"
    if [[ -f "$DATA/$SBID/data_quality.txt" ]]; then
        QUALITY=$(<"$DATA/$SBID/data_quality.txt")
    else
        QUALITY="NOT_VALIDATED"
    fi
    # Make a JSON of Metadata
printf '{\n  "SBID": "%s",\n  "QUALITY": "%s",\n  "COMMENT": "%s",\n  "RUN_TYPE": "%s"\n}\n' "$SBID" "$QUALITY" "$COMMENT" "$RUN_TYPE" > "$WORKDIR/metadata.json"
    # Zip it all up for transfer
    echo "Zipping ${WORKDIR} in staging area"
    tar -czf "${WORKDIR}.tar.gz" -C "$(dirname "$WORKDIR")" "$(basename "$WORKDIR")" && rm -rf "$WORKDIR"

    # Mark it as complete for the poller
    echo "Marking zip in staging area as ready to transfer"
    touch "$(dirname "$WORKDIR")/$(basename "$WORKDIR").complete"


done
echo "Completed data transfer preperation for ${SBIDARRAY[@]}"

# Stash the SLURM logs
echo "Checking for old SLURM logs"
mv slurm-*.out $DATA/tmp/
#exit 0
