#!/bin/bash

#SBATCH --time=06:00:00
#SBATCH --job-name=pilot2_upload
#SBATCH --output=/scratch/ja3/ger063/data/db_output.log
#SBATCH --error=/scratch/ja3/ger063/data/db_error.log
#SBATCH -N 1 # nodes
#SBATCH -n 1 # tasks
#SBATCH --cpus-per-task 2
#SBATCH --mem=75G

cd /scratch/ja3/ger063/data/
module load miniocli/2022-10-29T10-09-23Z
module load py-boto3/1.18.12
source /software/projects/ja3/ger063/setonix/python/bin/activate

srun python3 ~/upload_old_surveys.py
