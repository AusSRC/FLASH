#!/bin/bash


#######################################################################################################
source $HOME/set_local_flash_env.sh

echo "Checking for bad ascii files on HPC"

# copy current bad_files.json to the HPC for merging with new data
scp $CRONDIR/bad_files/bad_files.json $HPC_USER@$HPC_PLATFORM:~/src/linefinder/current_bad_files.json

# Run the HPC script to create new json file
ssh $HPC_USER@$HPC_PLATFORM "cd ~/src/linefinder; python3 process_bad_file_dir.py $HPC_SCRATCH/bad_ascii_files current_bad_files.json"

# Retrieve the new json file from HPC
scp $HPC_USER@$HPC_PLATFORM:~/src/linefinder/bad_files.json $CRONDIR/bad_files/

echo "Done!"
