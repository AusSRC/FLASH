#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_slurm_spectral.sh", which calls:
#                   2) "run_container_spectral.sh", which calls:
#                       3) a singularity container running "run_spectrals.sh"
#
######################################################################################
######################################################################################

# pass to container script: 
#   1) parent input data directory (holds the sbid, noise, catalogues subdirectories)
#   2) string of sbids to process
#   3) plot_spectral config directory (holds config.py)
jid1=$(/bin/bash ./run_container_spectral.sh /scratch/ja3/ger063/data "43424" /scratch/ja3/ger063/flash/config1)
jid2=$(/bin/bash ./run_container_spectral.sh /scratch/ja3/ger063/data "41050 42300" /scratch/ja3/ger063/flash/config2)

j1=$(echo $jid1 | awk '{print $4}')
j2=$(echo $jid2 | awk '{print $4}')
echo "Sumbitted jobs"
echo $j1
echo $j2

