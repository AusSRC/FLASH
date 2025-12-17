#!/bin/bash

# User's CASDA creds
CASDA_EMAIL="user@email"
export CASDA_EMAIL
CASDA_PWD="password_at_CASDA"
export CASDA_PWD

# Database details (usually accessed via client machine)
FLASHPASS="aussrc"
export FLASHPASS
HOST="10.0.2.225"
PORT="5432"

# Set HPC path to FLASH code
FLASHHOME=/software/projects/ja3/ger063/setonix/FLASH
# This path is for the CLIENT platform
#FLASHHOME=/home/flash/src/FLASH
export FLASHHOME

# Set data dir for this machine
DATA=/mnt/db/data/casda
export DATA

# Tmp dir for this machine
TMPDIR=/mnt/db/data/tmp
export TMPDIR

# Set path to cron scripts
CRONDIR=$HOME/src/cronjobs
export CRONDIR

# Client machine paths (eg Oracle VM)
CLIENTTMP=/mnt/db/data/tmp
export CLIENTTMP
CLIENTDATA=/mnt/db/data/casda
export CLIENTDATA
CLIENTIP="152.67.97.254"
export CLIENTIP
CLIENTKEY="~/.ssh/oracle_flash_vm.key"
export CLIENTKEY

# Other HPC machine paths (eg setonix)
HPC_PLATFORM="setonix.pawsey.org.au"
export HPC_PLATFORM
HPC_USER="user_at_hpc"
export HPC_USER
HPC_SCRATCH="/scratch/ja3/$HPC_USER/data/casda"
export HPC_SCRATCH
HPCDATA=$HPC_SCRATCH
export HPCDATA

# Set the DATA directory for this machine - uncomment ONE of these:
#DATA=$CLIENTDATA
#DATA=$HPCDATA
export DATA

# Set a TMP dir based on client/hpc role - uncomment ONE of these:
#TMPDIR=$CLIENTTMP
#TMPDIR=$DATA/tmp
export TMPDIR

# Blacklisted SBIDS directory
BLACKLIST_DIRS=$DATA/blacklist_sbids
export BLACKLIST_DIRS
# Set HPC path to spectral plotting software and container
SPECTRAL=$FLASHHOME/spectral_plot
export SPECTRAL

# Set HPC path to FLASH FINDER
FINDER=$FLASHHOME/flash_finder/flash_finder
export FINDER

# Set HPC path to pymultinest
PYMULTINEST=$FLASHHOME/pymultinest/20180215/
export PYMULTINEST

# Set HPC path to MULTINEST
export MULTINEST=$FLASHHOME/multinest

# Set HPC path to database scripts
FLASHDB=$FLASHHOME/database
export FLASHDB

# Add MultiNest library to dynamic library path
export DYLD_LIBRARY_PATH=$MULTINEST/lib:${DYLD_LIBRARY_PATH}
export LD_LIBRARY_PATH=$MULTINEST/lib:${LD_LIBRARY_PATH}


