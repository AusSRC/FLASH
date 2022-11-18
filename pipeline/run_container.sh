#!/bin/bash

#SBATCH --job-name=flashfinder
#SBATCH --output=/mnt/shared/flash/logs/finder_output_%j.log
#SBATCH --error=/mnt/shared/flash/logs/finder_error_%j.log
#SBATCH -N 1 # nodes
#SBATCH -n 1 # tasks
#SBATCH --cpus-per-task 28
#SBATCH --mem=75G

module load singularity
singularity exec --bind $2:/data,$3:/config linefinder.sif /home/flash/FLASH/pipeline/$1
