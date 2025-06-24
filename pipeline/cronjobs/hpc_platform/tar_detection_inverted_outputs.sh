#!/bin/bash
###############################################################
# This script will tar up the inverted linefinder outputs directory of a given SBID
# ############################################################
# $@ is the sbid(s) to process
SBIDARRAY=( "$@" )

for SBID1 in "${SBIDARRAY[@]}"; do
    echo "Tarring $SBID1 inverted linefinder results"
    cd $DATA/$SBID1/inverted_outputs; tar -zcvf inverted_linefinder.tar.gz results* *stats.dat *.pdf; mv inverted_linefinder.tar.gz ../
done
exit 0
