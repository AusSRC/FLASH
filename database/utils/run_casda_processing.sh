#!/bin/bash
#SBATCH --time=2:00:00
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --job-name=casda_proc
#SBATCH --no-requeue
#SBATCH --output=logs/out_casda_process.log
#SBATCH --error=logs/err_casda_process.log

PARENT_DIR="/scratch/ja3/ger063/data/casda"
USERNAME="Gordon.German@csiro.au"
PASS="Haggis15"

source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh
mkdir -p logs

jid=$(srun python3 $FLASHDB/db_utils.py -m GETNEWSBIDS -e $USERNAME -p $PASS -d $PARENT_DIR)
j1=$(echo $jid | awk '{print $4}')
echo "Sumbitted job"
echo $j1

# Dependent process job
jid2=$(sbatch --dependency=afterok:$j1 process_sbids.sh $PARENT_DIR)
j2=$(echo $jid2 | awk '{print $4}')
echo "Sumbitted job"
echo $j2

