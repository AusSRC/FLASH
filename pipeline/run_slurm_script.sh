#!/bin/bash

# pass to container script: 
#   1) the linefinder script (absorption or inverted)
#   2) input data directory
#   3) linefinder config directory (holds sources.log and model .txt)
jid1=$(/bin/bash ./run_container.sh absorption /scratch/ja3/ger063/flash/data4 /scratch/ja3/ger063/flash/config3)
jid2=$(/bin/bash ./run_container.sh absorption /scratch/ja3/ger063/flash/data4 /scratch/ja3/ger063/flash/config4)
jid3=$(/bin/bash ./run_container.sh absorption /scratch/ja3/ger063/flash/data4 /scratch/ja3/ger063/flash/config5)

j1=$(echo $jid1 | awk '{print $4}')
j2=$(echo $jid2 | awk '{print $4}')
j3=$(echo $jid3 | awk '{print $4}')
echo "Sumbitted jobs"
echo $j1
echo $j2
echo $j3

jid4=$(sbatch --dependency=afterok:$j1:$j2:$j3 collect_results.sh /scratch/ja3/ger063/flash/data4)

