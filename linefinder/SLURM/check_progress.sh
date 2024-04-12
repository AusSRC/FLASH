#!/bin/bash
#
##########################################################################################
#
#       Script to check progress of multiple linefinder jobs running on SLURM
#       GWHG @ CSIRO, Feb 2024
#       
#       eg: ./check_progress /scratch/ja3/ger/my_parent_dir 100 55247 55328 55394 55398
#
# Args  $1 = number of processes in mpi call (usually 100)
#       $2 ~ end = SBIDS to examine (logfile is assumed to be in SBID/logs/out.log - if not, edit DEFAULTLOG)
#
DEFAULTLOG="logs/out.log"

##########################################################################################
SBIDARRAY=(${@:3})
PARENTDIR=$1
range=$2
minr=0
maxr=$((range-1))
cwd=$PWD
cd $PARENTDIR

echo
for SBID1 in "${SBIDARRAY[@]}"; do
    echo "$SBID1: "
    LOGDIR=$SBID1/$DEFAULTLOG
    running=0

    var="$(grep -F 'End of CPU' $LOGDIR | awk '{print $4}')" 

    for (( i=$minr; i<=$maxr; i++ ))
    do
        if echo "$var" | grep -qw "$i"; then
            :
        else
            str1="CPU $i: Working on Source"
            var2="$(grep -A 1 "$str1" $LOGDIR | tail -1)"
            echo "    CPU $i not finished: $var2"
            running=$((running+1))
        fi

    done

    if [ ! $running == 0 ]
    then
        echo "    $running of $range processes still running"
    fi
    var3="$(grep -F 'Linefinder took' $LOGDIR)"
    var4="$(grep -F 'MPICH Slingshot Network Summary: 0' $LOGDIR)"
    if [ ! -z "$var4" ] 
    then
        if [ $running == 0 ]
        then
            echo "    Linefinder finished and SLURM jobs exited"
        else
            echo "    Linefinder has exited but not all processes finished!! "
        fi
    fi
    if [ -z "$var4" ] && [ ! -z "$var3" ]
    then
        echo "    Linefinder finished but SLURM has not exited correctly"
        echo "    You may need to manually scancel this SLURM job - see 'jobs_to_sbids.txt' to find SLURM job number"
    fi
done
cd $cwd
echo
