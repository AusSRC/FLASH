
#!/bin/bash
#
##########################################################################################
#
#       Script to check progress of multiple linefinder jobs running on SLURM
#       GWHG @ CSIRO, May 2024
#       
#       eg: ./check_progress /scratch/ja3/ger/my_parent_dir out.log 55247 55328 55394 55398
#
# Args  $1 = name of logfile (not path) eg 'out.log'
#       $2 = 'v' or 's' = verbose or shortform
#       $3 ~ end = SBIDS to examine 
#
range=100 # The number of mpi connections in the sbatch call

##########################################################################################
SBIDARRAY=(${@:3})
DEFAULTLOG="logs/$1"
LONGFORM=true # Set to 'true' to get current components being worked on for each process
if [ "$2" = "s" ]; then
    LONGFORM=false
fi
PARENTDIR=$DATA
minr=0
maxr=$((range-1))
not_started=()
started=()
finished=()
cwd=$PWD
cd $PARENTDIR

echo
for SBID1 in "${SBIDARRAY[@]}"; do
    echo "$SBID1: "
    LOGDIR=$SBID1/$DEFAULTLOG
    running=0
    prelim=0

    var="$(grep -F 'End of CPU' $LOGDIR | awk '{print $4}')" 

    for (( i=$minr; i<=$maxr; i++ ))
    do
        if echo "$var" | grep -qw "$i"; then
            :
        else
            str1="CPU $i: Working on Source"
            var2="$(grep -A 1 "$str1" $LOGDIR | tail -1)"
            if [ -z "${var2}" ]
            then
                prelim=$((prelim+1))
            else
                if $LONGFORM; then
                    echo "    CPU $i not finished: $var2"
                fi
                running=$((running+1))
            fi
        fi

    done

    if [ ! $running == 0 ]
    then
        
        echo "    $running of $range processes still running"
        started+=(" $SBID1: $running of $range processes still running\n")
    else
        not_started+=($SBID1)
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
        not_started=("${not_started[@]/$SBID1}" )
        finished+=($SBID1)
    fi
    if [ -z "$var4" ] && [ ! -z "$var3" ]
    then
        echo "    Linefinder finished but SLURM has not exited correctly"
        echo "    You may need to manually scancel this SLURM job - see 'jobs_to_sbids.txt' to find SLURM job number"
        not_started=("${not_started[@]/$SBID1}" )
        finished+=($SBID1)
    fi
done

i=1
echo -e "\nRUNNING:\n"
for j in ${!started[@]}; do
    echo "$i: ${started[$j]}"
    i=$((i+1))
done
echo
i=1
echo -e "Finished:\n"
for j in ${!finished[@]}; do
    echo "$i: ${finished[$j]}"
    i=$((i+1))
done

i=1
echo -e "\nNOT STARTED:\n"
for j in ${!not_started[@]}; do
    if [ ! -z ${not_started[$j]} ]
    then
        echo "$i: ${not_started[$j]}"
        i=$((i+1))
    fi
done

if [ $running == 0 ] && [ $not_started == 0 ]
then
        echo "All jobs finished!!"
else
        echo "Some jobs not finished (or not started)"
fi



cd $cwd
echo
