# Set path to FLASH FINDER
FINDER=$HOME/src/FLASH/linefinder 
export FINDER

# Set path to MULTINEST
export MULTINEST=$HOME/src/FLASH/PyMultinest/MultiNest

# Set path to PYMULTINEST
export PYMULTINEST=$HOME/src/FLASH/PyMultinest

# Add MultiNest library to dynamic library path
export DYLD_LIBRARY_PATH=$MULTINEST/lib:${DYLD_LIBRARY_PATH}
export LD_LIBRARY_PATH=$MULTINEST/lib:${LD_LIBRARY_PATH}

# Set path to Matplotlib set up
export MATPLOTLIBRC=$HOME/.local/lib/python3.10/site-packages/matplotlib/

/usr/bin/env python3 $FINDER/flash_finder_NOMPI.py \
--x_units 'frequency' \
--rest_frequency '1420.405752' \
--y_units 'abs' \
--out_path $FINDER'/testing/chains' \
--data_path $FINDER'/testing/data/33616/spectra_ascii' \
--sourcelog 'sources1.log' \
--model_path $FINDER/'model.txt' \
--nlive 1000 \
--channel_function 'none' \
--plot_restframe 'peak' \
--noise_factor '1.00' \
--small_plots \
--detection_limit 0. \
--mmodal \
