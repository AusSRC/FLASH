#!/bin/bash

# Set path to Matplotlib set up
#export MATPLOTLIBRC=$HOME/.local/lib/python3.10/site-packages/matplotlib/

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
--invert_spectra \
