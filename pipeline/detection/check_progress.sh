
#!/bin/bash
#
##########################################################################################
#
#       Script to check progress of multiple linefinder jobs running on SLURM
#       GWHG @ CSIRO, May 2024
#       
#       eg: ./check_progress /scratch/ja3/ger/my_parent_dir out.log 55247 55328 55394 55398
#
# Args  $1 = mode - one of STD, INVERT or MASK
#       $2 = 'v' or 's' = verbose or shortform
#       $3 ~ end = SBIDS to examine 
#
range=100 # The number of mpi connections in the sbatch call

##########################################################################################
source $HOME/set_local_flash_env.sh
SBIDARRAY=(${@:3})
DEFAULTLOG="logs/out.log"
MODE=$1
if [ "$MODE" = "INVERT" ]; then
    DEFAULTLOG="logs/out_inverted.log"
elif [ "$MODE" = "MASK" ]; then
    DEFAULTLOG="logs/out_masked.log"
fi

DEFAULTERR="${DEFAULTLOG/out/err}"
LONGFORM=true # Set to 'true' to get current components being worked on for each process
if [ "$2" = "s" ]; then
    LONGFORM=false
fi
PARENTDIR=$DATA
minr=0
maxr=$((range-1))
not_started=()
started=()
sbids_started=()
finished=()
error=()
cwd=$PWD
cd $PARENTDIR

echo
for SBID1 in "${SBIDARRAY[@]}"; do
    echo "$SBID1: "
    OUTLOG=$SBID1/$DEFAULTLOG
    ERRLOG=$SBID1/$DEFAULTERR
    running=0
    prelim=0

    var="$(grep -F 'End of CPU' $OUTLOG | awk '{print $4}')" 

    for (( i=$minr; i<=$maxr; i++ ))
    do
        if echo "$var" | grep -qw "$i"; then
            :
        else
            str1="CPU $i: Working on Source"
            var2="$(grep -A 1 "$str1" $OUTLOG | tail -1)"
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
        
        echo "    $running of $range processes still not finished"
        started+=(" $SBID1: $running of $range processes still not finished\n")
        sbids_started+=($SBID1)
    else
        not_started+=($SBID1)
    fi

    var3="$(grep -F 'Linefinder took' $OUTLOG)"
    var4="$(grep -F 'MPICH Slingshot Network Summary: 0' $OUTLOG)"
    var5="$(grep -F 'Error configuring interconnect' $ERRLOG)"
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
    if [ ! -z "$var5" ]
    then
        error+=($SBID1)
    fi
done

i=1
echo -e "\nRUNNING:"
for j in ${!started[@]}; do
    sbid=${sbids_started[$j]}
    sque="$(squeue -u $USER | grep nid | grep $sbid)"
    if [ ! -z "$sque" ]; then
        echo "$i: ${started[$j]}"
        i=$((i+1))
    else
        failed+=($sbid)
    fi
done
running=$((i-1))

echo
i=1
echo -e "Finished:"
for j in ${!finished[@]}; do
    echo "$i: ${finished[$j]}"
    i=$((i+1))
done

if [ -z "$running" ] && [ -z "$not_started" ] && [ -z "$error" ] && [ -z "$failed" ]
then
        echo -e "\nAll jobs finished!!"
elif [ -z "$not_started" ] && [ -z "$error" ]
then
        echo -e "\nAll jobs were started"
else
        echo -e "\nSome jobs errored or not started"
fi

i=1
echo -e "\nNOT STARTED:"
for j in ${!not_started[@]}; do
    if [ ! -z ${not_started[$j]} ]
    then
        echo "$i: ${not_started[$j]}"
        i=$((i+1))
    fi
done

i=1
echo -e "\nMPI ERRORED:"
for j in ${!error[@]}; do
    if [ ! -z ${error[$j]} ]
    then
        echo "$i: ${error[$j]}"
        i=$((i+1))
    fi
done
if [ ! -z "$error" ]; then
    declare -p error > "$HOME/src/linefinder/${MODE}_error_mpi_sbids.sh"
    #echo "${error[@]}" > $HOME/src/linefinder/${MODE}_error_mpi_sbids.txt
fi
i=1
echo -e "\nTIMED OUT (or removed from SLURM):"
for j in ${!failed[@]}; do
    echo "$i: ${failed[$j]}"
    i=$((i+1))
done
if [ ! -z "$failed" ]; then
    declare -p failed > "$HOME/src/linefinder/${MODE}_failed_mpi_sbids.sh"
    #echo ${failed[@]} > $HOME/src/linefinder/${MODE}_failed_sbids.txt
fi

echo


cd $cwd
echo
