#!/bin/bash

# Set path to FLASH code
FLASHHOME=$HOME/src/FLASH
export FLASHHOME

# Set path to FLASH FINDER
FINDER=$FLASHHOME/linefinder 
export FINDER

# Set path to MULTINEST
export MULTINEST=$FLASHHOME/PyMultiNest/MultiNest

# Set path to PYMULTINEST
export PYMULTINEST=$FLASHHOME/PyMultiNest

# Add MultiNest library to dynamic library path
export DYLD_LIBRARY_PATH=$MULTINEST/lib:${DYLD_LIBRARY_PATH}
export LD_LIBRARY_PATH=$MULTINEST/lib:${LD_LIBRARY_PATH}

