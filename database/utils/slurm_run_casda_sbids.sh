#!/bin/bash
######################################################################################
######################################################################################
#
#       Check CASDA for new sbids and if available, download the catalogue, noise and spectra
#
#   This script will perform the following:
#       1. Create sbid subdirectories under the declared parent directory
#       2. Download the required CASDA data and untar all tarballs
#
#       The script expects a parent directory to exist ("PARENT_DIR", see below), under 
#       which it will create all required sub-directories.
#
#
####################### USER EDIT VALUES #############################################

# The parent directory holding the SBIDS
PARENT_DIR="/scratch/ja3/ger063/data/casda"

# CASDA authentication
USERNAME="Gordon.German@csiro.au"
PASS="Haggis15"

#####################################################################################
############### DO NOT EDIT FURTHER #################################################

source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh

sbatch <<EOT
#!/bin/bash
#SBATCH --time=2:00:00
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --job-name=casda_get
#SBATCH --no-requeue
#SBATCH --output=logs/"$1"get_casda_out.log
#SBATCH --error=logs/"$1"get_casda_err.log

source /software/projects/ja3/ger063/setonix/python/bin/activate

export SLURM_EXPORT_ENV=ALL

echo "Checking CASDA for valid SBIDS"
python3.9 $FLASHDB/db_utils.py -m CATALOGUE -s $1 -e $USERNAME -p $PASS -d $PARENT_DIR -pw $2 -r

exit 0
EOT
