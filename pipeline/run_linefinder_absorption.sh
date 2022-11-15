#!/bin/bash
#SBATCH --job-name=linefinder
#SBATCH -N 1 # nodes
#SBATCH -n 1 # tasks
#SBATCH --cpus-per-task 28
#SBATCH --mem=32G

# Set path to Matplotlib set up
#export MATPLOTLIBRC=$HOME/.local/lib/python3.10/site-packages/matplotlib/

module load python/3.9.1

/usr/bin/env python3 $FINDER/flash_finder_NOMPI.py \
--x_units 'frequency' \
--rest_frequency '1420.405752' \
--y_units 'abs' \
--out_path $1 \
--data_path $2 \
--sourcelog $3 \
--model_path $4 \
--nlive 1000 \
--channel_function 'none' \
--plot_restframe 'peak' \
--noise_factor '1.00' \
--small_plots \
--detection_limit 0. \
--mmodal \
