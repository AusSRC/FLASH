#!/bin/bash
###############################################################
# This script will tar up the spectra_ascii and spectra_plots directory
# of a given SBID
# ############################################################
# $1 is the SBID
#
echo "Tarring $1 spectral plot results"

cd $DATA/$1/spectra_ascii; tar -zcvf $1_ascii_tarball.tar.gz *; mv $1_ascii_tarball.tar.gz ../
cd $DATA/$1/spectra_plots; tar -zcvf $1_plots_tarball.tar.gz *; mv $1_plots_tarball.tar.gz ../
cd $DATA/$1/SourceSpectra; tar -zcvf $1_sources_tarball.tar.gz *; mv $1_sources_tarball.tar.gz ../
exit 0
