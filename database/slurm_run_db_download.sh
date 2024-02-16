#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_db_download.sh", which calls:
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
#SBATCH --job-name=db_upload
#SBATCH --no-requeue
#SBATCH --output=logs/"$1"_db_down_out.log
#SBATCH --error=logs/"$1"_db_down_err.log

source /software/projects/ja3/ger063/setonix/python/bin/activate

export SLURM_EXPORT_ENV=ALL

echo "Downloading $1 spectral ascii files from database"
python $FLASHDB/db_download.py -m ASCII -s '$1' -d '$2' -t

echo "Checking for bad files"
python $FINDER/pre_process.py '$3' '$2'

exit 0
EOT
