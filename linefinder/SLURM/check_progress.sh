#!/bin/bash
#
# Args: $1 = logfile to examine
#       $2 = number of processes in mpi call (usually 100)
#
range=$2
minr=0
maxr=$((range-1))
running=0

var="$(grep -F 'End of CPU' $1 | awk '{print $4}')" 

for (( i=$minr; i<=$maxr; i++ ))
do
    if echo "$var" | grep -qw "$i"; then
        echo "    CPU $i finished"
    else
        str1="CPU $i: Working on Source"
        var2="$(grep -A 1 "$str1" $1 | tail -1)"
        echo "CPU $i not finished: $var2"
        running=$((running+1))
    fi

done

echo "$running of $range processes still running"
var3="$(grep -F 'Linefinder took' $1)"
var4="$(grep -F 'MPICH Slingshot Network Summary: 0' $1)"
if [ ! -z "$var4" ]
then
    echo "Linefinder finished and SLURM jobs exited"
fi
if [ -z "$var4"] && [ ! -z "$var3" ]
then
    echo "Linefinder finished but SLURM has not exited correctly"
    echo "You should manually scancel this SLURM job"
fi
