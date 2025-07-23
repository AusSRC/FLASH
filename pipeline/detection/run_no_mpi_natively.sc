#!/bin/bash -l
#SBATCH --time=12:00:00
#SBATCH -N 1 # nodes
#SBATCH -n 1 # tasks
#SBATCH --cpus-per-task 31
#SBATCH --mem=100G
#SBATCH --job-name=nompi_1000_3_2
#SBATCH --no-requeue
#SBATCH --output=/scratch/ja3/ger063/flashfinder_nompi_test/out1000_3_2.log
#SBATCH --error=/scratch/ja3/ger063/flashfinder_nompi_test/err1000_3_2.log

module load python/3.9.15
module load py-numpy/1.20.3
module load py-matplotlib/3.4.3
module load py-astropy/5.1
module load py-mpi4py/3.1.2-py3.9.15

module load gcc/12.1.0
module load py-scipy/1.7.1

mkdir -p /scratch/ja3/ger063/flashfinder_nompi_test/chains_1000_3/absorption/

source ~/set_local_flash_env.sh

srun python3 $FINDERNOMPI/flash_finder_NOMPI.py \
--inifile /scratch/ja3/ger063/flashfinder_nompi_test/config/linefinder.ini

