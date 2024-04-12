#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_mpi_native_script.sh", which calls:
#                   2) "slurm_run_flashfinder.sh" (this file)
#
######################################################################################
######################################################################################
# Source the local env script - edit path if required
source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh

# Output directory:
mkdir -p "$1"/outputs
mkdir -p "$1"/logs

sbatch <<EOT
#!/bin/bash
#SBATCH --time=12:00:00
#SBATCH --ntasks=100
#SBATCH --ntasks-per-node=20
#SBATCH --job-name=FLASHFINDER_mpi
#SBATCH --no-requeue
#SBATCH --output="$1"/logs/out.log
#SBATCH --error="$1"/logs/err.log

module load python/3.10.10
module load py-numpy/1.23.4
module load py-matplotlib/3.6.2
module load py-astropy/5.1
module load py-mpi4py/3.1.4-py3.10.10

module load gcc/12.2.0
module load py-scipy/1.8.1


## Set the path variables for FLASHFINDER:
source /software/projects/ja3/ger063/setonix/FLASH/set_local_env.sh

export MPICH_GNI_MALLOC_FALLBACK=enabled
export MPICH_OFI_STARTUP_CONNECT=1
export MPICH_OFI_VERBOSE=1
export FI_CXI_DEFAULT_VNI=$(od -vAn -N4 -tu < /dev/urandom)
export SLURM_EXPORT_ENV=ALL

echo "Checking for bad files"
python $FINDER/pre_process.py '$3' '$1/$2'


echo "Starting with $1/$2"
## Ensure the correct linefinder.ini is specified here:
srun -K1 python $FINDER/flash_finder.py --data_path '$1/$2' --model_path '$1/config/model.txt' --out_path '$1/outputs' \
--inifile '$1/config/slurm_linefinder.ini'

exit 0
EOT
