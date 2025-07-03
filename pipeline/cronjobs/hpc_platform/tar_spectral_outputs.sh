#!/bin/bash
###############################################################
# This script will tar up the spectra_ascii and spectra_plots directory
# of a given SBID
# ############################################################
# $@ is the sbid(s) to process
SBIDARRAY=( "$@" )

for SBID1 in "${SBIDARRAY[@]}"; do

    echo "Tarring $SBID1 spectral plot results"

    cd $DATA/$SBID1/spectra_ascii; tar -zcvf "$SBID1"_ascii_tarball.tar.gz *; mv "$SBID1"_ascii_tarball.tar.gz ../
    cd $DATA/$SBID1/spectra_plots; tar -zcvf "$SBID1"_plots_tarball.tar.gz *; mv "$SBID1"_plots_tarball.tar.gz ../
    cd $DATA/$SBID1/SourceSpectra; tar -zcvf "$SBID1"_sources_tarball.tar.gz *; mv "$SBID1"_sources_tarball.tar.gz ../
done
exit 0
