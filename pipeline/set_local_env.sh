# Set path to FLASH FINDER
export FINDER=/home/flash/linefinder/ 

# Set path to MULTINEST
export MULTINEST=/home/flash/PyMultiNest/MultiNest/

# Set path to PYMULTINEST
export PYMULTINEST=/home/flash/PyMultiNest/

# Add MultiNest library to dynamic library path
export DYLD_LIBRARY_PATH=$MULTINEST/lib:${DYLD_LIBRARY_PATH}
export LD_LIBRARY_PATH=$MULTINEST/lib:${LD_LIBRARY_PATH}

# Set path to Matplotlib set up
#export MATPLOTLIBRC=$HOME/.local/lib/python3.10/site-packages/matplotlib/
