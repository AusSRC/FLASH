#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "detection_processing.sh", which calls:
#                   2) "slurm_run_db_download.sh" (this file)
#
######################################################################################
######################################################################################
mkdir -p logs
sbatch <<EOT
#!/bin/bash
#SBATCH --time=1:00:00
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --job-name=oracle_download
#SBATCH --no-requeue
#SBATCH --output=logs/"$1"_oracle_down_out.log
#SBATCH --error=logs/"$1"_oracle_down_err.log

source /software/projects/ja3/ger063/setonix/python/bin/activate

export SLURM_EXPORT_ENV=ALL

echo "ssh'ing into Oracle with python3.9 /home/flash/src/database/db_download.py -m ASCII -s '$1' -d '$2' -pw '$4' -t"

ssh -i $FLASHDB/oracle_flash_vm.key flash@152.67.97.254 "cd ~/tmp; python3.9 /home/flash/src/database/db_download.py -m ASCII -s '$1' -d '$2' -pw '$4' -t;"
echo "Downloading $1 spectral ascii files from Oracle database"
scp -i $FLASHDB/oracle_flash_vm.key flash@152.67.97.254:~/tmp/'$1'*.tar.gz .

echo "Checking for bad files"
python $FINDER/pre_process.py '$3' '$2'

exit 0
EOT
