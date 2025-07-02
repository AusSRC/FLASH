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
DATA=/mnt/casda
export DATA

# Tmp dir
TMPDIR=/mnt/tmp
export TMPDIR

# Blacklisted SBIDS directory
BLACKLIST_DIRS=$DATA/blacklist_sbids
export BLACKLIST_DIRS
