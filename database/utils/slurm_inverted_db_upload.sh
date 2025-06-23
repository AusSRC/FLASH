#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_db_upload.sh", which calls:
#                   2) "slurm_linefinder_db_upload.sh" (this file)
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
#SBATCH --output=logs/"$1"_db_upload_out.log
#SBATCH --error=logs/"$1"_db_upload_err.log

source /software/projects/ja3/ger063/setonix/python/bin/activate

export SLURM_EXPORT_ENV=ALL

echo "Uploading $1 linefinder results to database"
echo "Starting with $FLASHDB/db_upload.py -m INVERTED -s '$1' -cl '$5'/'$1'/'$2' -o '$3' -r '$5'/'$1'/'$4' -p '$6' -C '$7' -pw '$8'"
python3.9 $FLASHDB/db_upload.py -m INVERTED -s '$1' -cl '$5'/'$1'/'$2' -o '$3' -r '$5'/'$1'/'$4' -p '$6' -C "$7" -pw '$8' 

exit 0
EOT
