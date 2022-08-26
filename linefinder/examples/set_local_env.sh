# Set path to FLASH FINDER
FINDER=$HOME/src/FLASH/linefinder/ 
export FINDER

# Set path to MULTINEST
export MULTINEST=$HOME/src/FLASH/PyMultinest/MultiNest/

# Set path to PYMULTINEST
export PYMULTINEST=$HOME/src/FLASH/PyMultinest/

# Add MultiNest library to dynamic library path
export DYLD_LIBRARY_PATH=$MULTINEST/lib:${DYLD_LIBRARY_PATH}
# export LD_LIBRARY_PATH=$MULTINEST/lib:${LD_LIBRARY_PATH}

# Set path to Matplotlib set up
export MATPLOTLIBRC=$HOME/.local/lib/python3.10/site-packages/matplotlib/
