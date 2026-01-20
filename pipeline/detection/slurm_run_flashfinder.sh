#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_mpi_native_script.sh",  or "detection_processing.sh" which calls:
#                   2) "slurm_run_flashfinder.sh" (this file), which directly calls the
#                       linefinder code.
#
######################################################################################
######################################################################################
# Source the local env script - edit path if required
source ~/set_local_flash_env.sh

MODE=$5
# Log directory:
mkdir -p "$1"/logs
cd "$1"

module unload gcc-native/14.2
module swap pawseyenv/2025.08 pawseyenv/2024.05
module load gcc/12.2.0
module load libfabric/1.15.2.0 

module load python/3.11.6 
module load py-matplotlib/3.8.1 
module load py-astropy/5.1 
module load py-mpi4py/3.1.5-py3.11.6 
module load gcc/12.2.0 
module load py-scipy/1.11.3 
module load py-numpy/1.24.4 

#module load python/3.11.6
#module load py-numpy/1.25.2
#module load py-scipy/1.14.1
#module load py-matplotlib/3.9.2
#module load py-astropy/5.1
#module load py-mpi4py/3.1.5-py3.11.6

#module load py-astropy/5.1
#module load py-mpi4py/3.1.5-py3.11.6



export MPICH_GNI_MALLOC_FALLBACK=enabled
export MPICH_OFI_STARTUP_CONNECT=1
export MPICH_OFI_VERBOSE=1
export FI_CXI_DEFAULT_VNI="$(od -vAn -N4 -tu < /dev/urandom)"
export SLURM_EXPORT_ENV=ALL

echo "Checking for bad files"
python3 $FLASHHOME/pre_process.py $3 $1/$2


echo "Starting with $1/$2"
## Ensure the correct linefinder.ini is specified here:
if [ "$MODE" = "STD" ]; then
    mkdir -p "$1"/outputs
    srun -K1 python3 $FINDER/flash_finder.py --data_path $1/$2 --model_path $1/config/model.txt --out_path $1/outputs \
--mask_path $1/config/mask.txt --sbid $4 --inifile $1/config/slurm_linefinder.ini
elif [ "$MODE" = "INVERT" ]; then
    mkdir -p "$1"/inverted_outputs
    srun -K1 python3 $FINDER/flash_finder.py --data_path $1/$2 --model_path $1/config/model.txt --out_path $1/inverted_outputs \
--mask_path $1/config/mask.txt --sbid $4 --inifile $1/config/slurm_linefinder_inverted.ini
elif [ "$MODE" = "MASK" ]; then
    mkdir -p "$1"/masked_outputs
    srun -K1 python3 $FINDER/flash_finder.py --data_path $1/$2 --model_path $1/config/model.txt --out_path $1/masked_outputs \
--mask_path $1/config/mask.txt --sbid $4 --inifile $1/config/slurm_linefinder.ini
fi

exit 0
EOT
