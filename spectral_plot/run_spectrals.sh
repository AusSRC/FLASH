#!/bin/bash

#SBATCH --job-name=plot_spectra
#SBATCH --output=/mnt/shared/flash_test/outputs/logs/plot_spectra_out%j.log
#SBATCH --error=/mnt/shared/flash_test/outputs/logs/plot_spectra_err%j.log
#SBATCH -N 1 # nodes
#SBATCH -n 1 # tasks
#SBATCH --cpus-per-task 30
#SBATCH --mem=25G

export LD_LIBRARY_PATH=/mnt/shared/flash_test/lib:$LD_LIBRARY_PATH
module load python/3.9.1
python3 plot_spectral.py --sbids $1 $2
