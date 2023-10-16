#!/bin/bash -l
#SBATCH --time=12:00:00
#SBATCH --ntasks=100
#SBATCH --ntasks-per-node=20
#SBATCH --job-name=1500_5_flash
#SBATCH --no-requeue
#SBATCH --output=/scratch/ja3/ger063/data/50000/out1500_5.log
#SBATCH --error=/scratch/ja3/ger063/data/50000/err1500_5.log

module load python/3.10.10
module load py-numpy/1.23.4
module load py-matplotlib/3.6.2
module load py-astropy/5.1
module load py-mpi4py/3.1.4-py3.10.10

module load gcc/12.2.0
module load py-scipy/1.8.1

## Output directory:
mkdir -p /scratch/ja3/ger063/data/50000/chains_1500_5/absorption/

## Set the path variables for FLASHFINDER:
source ~/set_local_env.sh

export MPICH_GNI_MALLOC_FALLBACK=enabled
export MPICH_OFI_STARTUP_CONNECT=1
export MPICH_OFI_VERBOSE=1
export FI_CXI_DEFAULT_VNI=$(od -vAn -N4 -tu < /dev/urandom)

## Ensure the correct linefinder.ini is specified here:
srun --export=ALL --ntasks=100 --ntasks-per-node=20 -c 1 python $FINDER/flash_finder.py \
--inifile '/scratch/ja3/ger063/flashfinder_test/config/linefinder1500_5.ini'
