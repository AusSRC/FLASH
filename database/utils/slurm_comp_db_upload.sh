#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_db_upload.sh", which calls:
#                   2) "slurm_plot_db_upload.sh" (this file)
#
######################################################################################
######################################################################################
mkdir -p logs

sbatch <<EOT
#!/bin/bash
#SBATCH --time=4:00:00
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --job-name=db_comp
#SBATCH --no-requeue
#SBATCH --output=logs/"$1"_db_comp_out.log
#SBATCH --error=logs/"$1"_db_comp_err.log

source /software/projects/ja3/ger063/setonix/python/bin/activate

export SLURM_EXPORT_ENV=ALL

echo "Uploading $1 components + plot results to database"
echo "Starting with $FLASHDB/db_upload.py -m COMPONENTS -s '$1' -d '$2' -pw '$3'"
python3.9 $FLASHDB/db_upload.py -m COMPONENTS -s '$1' -d '$2' -pw '$3'

exit 0
EOT
