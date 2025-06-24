#!/bin/bash
###############################################################
# This script will tar up the linefinder outputs directory of a given SBID
# ############################################################
# $@ is the sbid(s) to process
SBIDARRAY=( "$@" )

for SBID1 in "${SBIDARRAY[@]}"; do
    echo "Tarring $SBID1 linefinder results"
    cd $DATA/$SBID1/outputs; tar -zcvf linefinder.tar.gz results* *stats.dat *.pdf; mv linefinder.tar.gz ../
done
exit 0
