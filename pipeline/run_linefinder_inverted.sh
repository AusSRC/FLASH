#!/bin/bash
source /home/flash/FLASH/pipeline/set_local_env.sh

# Set path to Matplotlib set up
#export MATPLOTLIBRC=/home/flash/.local/lib/python3.10/site-packages/matplotlib/

/usr/bin/env python3 $FINDER/flash_finder_NOMPI.py \
--x_units 'frequency' \
--rest_frequency '1420.405752' \
--y_units 'abs' \
--out_path /data/outputs \
--data_path /data \
--sourcelog /config/sources.log \
--model_path /config/model.txt \
--nlive 1000 \
--channel_function 'none' \
--plot_restframe 'peak' \
--noise_factor '1.00' \
--small_plots \
--detection_limit 0. \
--mmodal \
--invert_spectra \

find . -type f -name "results_*.dat" -exec awk 'NR==1 || FNR>1' {} + > 'results_all.txt'


