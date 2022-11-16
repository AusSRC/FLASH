#!/bin/bash

/usr/bin/env python3 $FINDER/flash_finder_NOMPI.py \
--x_units 'frequency' \
--rest_frequency '1420.405752' \
--y_units 'abs' \
--out_path $FINDER/examples/chains \
--data_path $FINDER/examples/data \
--sourcelog 'sources.log' \
--model_path $FINDER/examples/model.txt \
--nlive 500 \
--channel_function 'none' \
--plot_restframe 'peak' \
--noise_factor '1.00' \
--small_plots \
--detection_limit 0. \
--mmodal \
