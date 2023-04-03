#!/bin/bash

# Set path to FLASH code
FLASHHOME=/home/flash/FLASH
export FLASHHOME

# Set path to FLASH FINDER
FINDER=$FLASHHOME/linefinder 
export FINDER

# Set path to PYMULTINEST
export PYMULTINEST=$FLASHHOME/PyMultiNest
# For MPI verison:
#export PYMULTINEST=$FLASHHOME/PyMultiNest_MPI

# Set path to MULTINEST
export MULTINEST=$PYMULTINEST/MultiNest

# Add MultiNest library to dynamic library path
export DYLD_LIBRARY_PATH=$MULTINEST/lib:${DYLD_LIBRARY_PATH}
export LD_LIBRARY_PATH=$MULTINEST/lib:${LD_LIBRARY_PATH}

