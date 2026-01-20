#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_slurm_scripts.sh", which calls:
#                   2) "run_container.sh", which calls:
#                       3) a singularity container running "run_linefinder.sh"
#
#           This is just an example script - the actual "run_linefinder.sh" script that 
#           is run during a job is INTERNAL TO the singularity container that is 
#           started by the "run_container.sh" scripts. Hence any changes to this 
#           script will have no effect on jobs started through the above scripts.
######################################################################################
######################################################################################
source ./set_local_flash_env.sh

# Set path to Matplotlib set up
#export MATPLOTLIBRC=/home/flash/.local/lib/python3.10/site-packages/matplotlib/

# NOTE: These command-line arguments are not overriden by the config files. All others are.
#       Do NOT change them!
/usr/bin/env python3 $FINDER/flash_finder_NOMPI.py \
--out_path /data/outputs \
--data_path /data \
--sourcelog /config/sources.log \
--model_path /config/model.txt \
