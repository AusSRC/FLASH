#!/bin/bash -l
#SBATCH --time=12:00:00
#SBATCH --ntasks=100
#SBATCH --ntasks-per-node=20
#SBATCH --job-name=flash_comp_test
#SBATCH --no-requeue
#SBATCH --output=/scratch/ja3/ger063/data/aditya/out_%j.log
#SBATCH --error=/scratch/ja3/ger063/data/aditya/err_%j.log

module load python/3.9.15
module load py-numpy/1.20.3
module load py-matplotlib/3.4.3
module load py-astropy/5.1
module load py-mpi4py/3.1.2-py3.9.15
module load gcc/12.1.0
module load py-scipy/1.7.1

source ~/set_local_env.sh
export MPICH_GNI_MALLOC_FALLBACK=enabled
export MPICH_OFI_STARTUP_CONNECT=1
export MPICH_OFI_VERBOSE=1
export FI_CXI_DEFAULT_VNI=$(od -vAn -N4 -tu < /dev/urandom)

srun --export=ALL --ntasks=100 --ntasks-per-node=20 -c 1 python $FINDER/flash_finder.py \
--inifile "/scratch/ja3/ger063/data/aditya/config/linefinder_$1.ini"


