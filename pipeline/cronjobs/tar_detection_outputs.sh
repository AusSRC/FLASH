#!/bin/bash
###############################################################
# This script will tar up the linefinder outputs directory of a given SBID
# ############################################################
# $1 is the SBID
#
echo "Tarring $1 linefinder results"

cd $DATA/$1/outputs; tar -zcvf $1_linefinder.tar.gz results* *stats.dat *.pdf; mv $1_linefinder.tar.gz ../
exit 0
