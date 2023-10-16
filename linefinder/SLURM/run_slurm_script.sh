#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_slurm_scripts.sh", which calls:
#                   2) "run_container.sh", which calls:
#                       3) a singularity container running "run_linefinder.sh"
#
######################################################################################
######################################################################################

# pass to container script: 
#   1) input data directory
#   2) linefinder config directory (holds linefinder.ini, sources.log and model .txt)
jid1=$(/bin/bash ./run_container.sh /scratch/ja3/ger063/flash/data4 /scratch/ja3/ger063/flash/config3)
jid2=$(/bin/bash ./run_container.sh /scratch/ja3/ger063/flash/data4 /scratch/ja3/ger063/flash/config4)
jid3=$(/bin/bash ./run_container.sh /scratch/ja3/ger063/flash/data4 /scratch/ja3/ger063/flash/config5)

j1=$(echo $jid1 | awk '{print $4}')
j2=$(echo $jid2 | awk '{print $4}')
j3=$(echo $jid3 | awk '{print $4}')

# dependent collection job:
jid4=$(sbatch --dependency=afterok:$j1:$j2:$j3 collect_results.sh /scratch/ja3/ger063/flash/data4)
j4=$(echo $jid4 | awk '{print $4}')

echo "Sumbitted jobs"
echo $j1
echo $j2
echo $j3
echo $j4


