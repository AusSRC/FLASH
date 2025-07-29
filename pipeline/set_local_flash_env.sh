#!/bin/bash

# Set path to FLASH code
FLASHHOME=/home/flash/src/FLASH
export FLASHHOME

# Set path to FLASH FINDER
FINDER=$FLASHHOME/linefinder
export FINDER

# Set path to database scripts
FLASHDB=$FLASHHOME/database
export FLASHDB

# Set path to cron scripts
CRONDIR=/home/flash/src/cronjobs
export CRONDIR

# Set data dir
DATA=/mnt/db/data/casda
export DATA

# Tmp dir
TMPDIR=/mnt/db/data/tmp
export TMPDIR

# Blacklisted SBIDS directory
BLACKLIST_DIRS=$DATA/blacklist_sbids
export BLACKLIST_DIRS

# User's CASDA creds
CASDA_EMAIL="user@email"
export CASDA_EMAIL
CASDA_PWD="password_at_CASDA"
export CASDA_PWD

# Client machine paths (eg Oracle VM)
CLIENTTMP=/mnt/db/data/tmp
export CLIENTTMP
CLIENTDATA=/mnt/db/data/casda
export CLIENTDATA
CLIENTIP="152.67.97.254"
export CLIENTIP
CLIENTKEY="~/.ssh/oracle_flash_vm.key"
export CLIENTKEY

# Database details (usually accessed via client machine)
FLASHPASS="aussrc"
export FLASHPASS
HOST="10.0.2.225"
PORT="5432"

# HPC machine paths (eg setonix)
HPC_PLATFORM="setonix.pawsey.org.au"
export HPC_PLATFORM
HPC_USER="user_at_hpc"
export HPC_USER
HPC_SCRATCH="/scratch/ja3/$HPC_USER/data/casda"
export HPC_SCRATCH
