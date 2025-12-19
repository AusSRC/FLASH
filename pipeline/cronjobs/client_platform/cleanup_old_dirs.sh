#!/bin/bash


#######################################################################################################
source $HOME/set_local_flash_env.sh

echo "Removing stale directories on client platform"

cd $DATA
find . -mindepth 1 -maxdepth 1 -type d ! -name "catalogues" ! -name "bad_ascii_files" ! -name "blacklist_sbids" -exec rm -rf {} \;
cd $TMPDIR
rm -R *

cd $CRONDIR; rm ../cron*.log

echo "Removing stale directories on HPC platform"


ssh $HPC_USER@$HPC_PLATFORM "cd $HPC_SCRATCH; find . -mindepth 1 -maxdepth 1 -type d ! -name 'catalogues' ! -name 'bad_ascii_files' -exec rm -rf {} \;"
ssh $HPC_USER@$HPC_PLATFORM "cd $HPC_SCRATCH; mkdir tmp"

echo "Done directory cleanup"
