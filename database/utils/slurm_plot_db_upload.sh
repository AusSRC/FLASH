#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_db_upload.sh", which calls:
#                   2) "slurm_plot_db_upload.sh" (this file)
#
######################################################################################
######################################################################################
# Get the CASDA-reported data quality (save in file 'data_quality.txt'
QUALITY=`cat "$5"/"$1"/data_quality.txt`
if [ -z "$QUALITY" ]; then
    QUALITY="NOT_VALIDATED"
fi
mkdir -p logs
source ~/setonix_set_local_env.sh

sbatch <<EOT
#!/bin/bash
#SBATCH --time=2:00:00
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --job-name=db_upload
#SBATCH --no-requeue
#SBATCH --output=logs/"$1"_db_upload_out.log
#SBATCH --error=logs/"$1"_db_upload_err.log

source ~/setonix_set_local_env.sh

export SLURM_EXPORT_ENV=ALL

echo "Uploading $1 spectral plot results to database"
echo "Starting with $FLASHDB/db_upload.py -m SPECTRAL -s '$1' -q '$QUALITY' -n '$2' -d '$5' -t '$3' -cs '$4' -p '$6' -C '$7' -pw '$8'"
python3.9 $FLASHDB/db_upload.py -m SPECTRAL -s '$1' -q '$QUALITY' -n '$2' -d '$5' -t '$3' -cs '$4' -p '$6' -C '$7' -pw '$8'

exit 0
EOT
