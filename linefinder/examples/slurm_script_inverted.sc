#!/bin/bash -l
#SBATCH --time=12:00:00
#SBATCH --ntasks=100
#SBATCH --ntasks-per-node=20
#SBATCH --job-name=15873_inv_flashfinder
#SBATCH --no-requeue
#SBATCH --export=NONE
#SBATCH --account=ja3

module load python
module load argparse
module load numpy
module load matplotlib
module load astropy
module unload PrgEnv-cray/6.0.4
module load mpi4py
module unload gcc
module load scipy
module use /group/askap/jallison/multinest/modulefiles
module load multinest
module use /group/askap/jallison/pymultinest/modulefiles
module load pymultinest
module use /group/askap/jallison/corner/modulefiles
module load corner
module use /group/askap/jallison/flash_finder/modulefiles
module load flash_finder

export MPICH_GNI_MALLOC_FALLBACK=enabled

srun --export=ALL --ntasks=100 --ntasks-per-node=20 python $FINDER/flash_finder.py \
--x_units 'frequency' \
--rest_frequency '1420.405752' \
--y_units 'abs' \
--out_path '/group/askap/FLASH/casda/15873/flash_finder/chains/inverted/' \
--data_path '/group/askap/FLASH/casda/15873/spectra/ascii_format/' \
--model_path '/group/askap/FLASH/casda/15873/flash_finder/model.txt' \
--nlive 1000 \
--channel_function 'none' \
--plot_restframe 'peak' \
--noise_factor '1.00' \
--mmodal \
--mpi_switch \
--small_plots \
--detection_limit 0. \
--invert_spectra \
