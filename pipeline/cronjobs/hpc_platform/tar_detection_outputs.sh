#!/bin/bash
###############################################################
# This script will tar up the linefinder outputs directory of a given SBID
# ############################################################
# $1 is the mode - STD, INVERT or MASK
MODE=$1
# rest of $@ is the sbid(s) to process
SBIDARR=( "$@" )
SBIDARRAY=${SBIDARR[@]:1}

for SBID1 in "${SBIDARRAY[@]}"; do
    if [ "$MODE" = "STD" ];then
        echo "Tarring $SBID1 linefinder results"
        cd $DATA/$SBID1/outputs; tar -zcvf linefinder.tar.gz results* *stats.dat *.pdf; mv linefinder.tar.gz ../
    elif [ "$MODE" = "INVERT" ]
        echo "Tarring $SBID1 inverted linefinder results"
        cd $DATA/$SBID1/inverted_outputs; tar -zcvf inverted_linefinder.tar.gz results* *stats.dat; mv inverted_linefinder.tar.gz ../
    elif [ "$MODE" = "MASK" ]
        echo "Tarring $SBID1 masked linefinder results"
        cd $DATA/$SBID1/masked_outputs; tar -zcvf masked_linefinder.tar.gz results* *stats.dat *.pdf; mv masked_linefinder.tar.gz ../
    fi
done
exit 0
