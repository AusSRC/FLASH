#!/bin/bash

# pass to container script: 
#   1) the linefinder script (absorption or inverted)
#   2) input data directory
#   3) linefinder config directory (holds sources.log and model .txt)
sbatch ./run_container.sh run_linefinder_absorption.sh /mnt/shared/flash/data3 /mnt/shared/flash/config3
sbatch ./run_container.sh run_linefinder_absorption.sh /mnt/shared/flash/data3 /mnt/shared/flash/config4
sbatch ./run_container.sh run_linefinder_absorption.sh /mnt/shared/flash/data3 /mnt/shared/flash/config5
