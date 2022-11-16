#!/bin/bash
# Set path to FLASH code
FLASHHOME=$HOME/src/FLASH
export FLASHHOME

# Set path to FLASH FINDER
FINDER=$FLASHHOME/linefinder 
export FINDER

# Set path to MULTINEST
export MULTINEST=$FLASHHOME/PyMultinest/MultiNest

# Set path to PYMULTINEST
export PYMULTINEST=$FLASHHOME/PyMultinest

# Add MultiNest library to dynamic library path
export DYLD_LIBRARY_PATH=$MULTINEST/lib:${DYLD_LIBRARY_PATH}
export LD_LIBRARY_PATH=$MULTINEST/lib:${LD_LIBRARY_PATH}

# Test directories
# Syntax is 'sbatch <scriptname> <output dir> <input dir> <source log name> <path to model.txt>
sbatch $FLASHHOME/pipeline/run_linefinder_absorption.sh /mnt/shared/flash_test/chains/33616 /mnt/shared/flash_test/outputs_test/33616/spectra_ascii sources1.log /mnt/shared/flash_test/model.txt

sbatch $FLASHHOME/pipeline/run_linefinder_absorption.sh /mnt/shared/flash_test/chains/34546 /mnt/shared/flash_test/outputs_test/34546/spectra_ascii sources1.log /mnt/shared/flash_test/model.txt

sbatch $FLASHHOME/pipeline/run_linefinder_absorption.sh /mnt/shared/flash_test/chains/34548 /mnt/shared/flash_test/outputs_test/34548/spectra_ascii sources1.log /mnt/shared/flash_test/model.txt
