#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_slurm_spectral.sh", which calls:
#                   2) "run_container_spectral.sh", which calls:
#                       3) a singularity container running "run_spectrals.sh"
#
#       This script (run_spectrals) is an example only. The live version is built into
#       the singularity container, therefore edits to this script will have no effect.
######################################################################################
######################################################################################


python3 plot_spectrals.py --sbids "$@"
