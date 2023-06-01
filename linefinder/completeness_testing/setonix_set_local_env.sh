#!/bin/bash

# Set path to FLASH code
FLASHHOME=/software/projects/ja3/ger063/setonix/FLASH
export FLASHHOME

# Set path to FLASH FINDER
FINDER=$FLASHHOME/flash_finder/flash_finder/
export FINDER

# Set path to FLASH FINDER NO MPI
FINDERNOMPI=$FLASHHOME/flash_finder/flash_finder_NO_MPI/
export FINDERNOMPI

# Set path to PYMULTINEST
export PYMULTINEST=$FLASHHOME/pymultinest/20180215
# For MPI verison:
#export PYMULTINEST=$FLASHHOME/PyMultiNest_MPI

# Set path to MULTINEST
export MULTINEST=$FLASHHOME/multinest

# Add MultiNest library to dynamic library path
export DYLD_LIBRARY_PATH=$MULTINEST/lib:${DYLD_LIBRARY_PATH}
export LD_LIBRARY_PATH=$MULTINEST/lib:${LD_LIBRARY_PATH}

