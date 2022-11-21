#!/bin/bash

sbatch <<EOT
#!/bin/bash
#SBATCH --job-name=flashfinder
#SBATCH --output="$2"/outputs/logs/finder_output_%j.log
#SBATCH --error="$2"/outputs/logs/finder_error_%j.log
#SBATCH -N 1 # nodes
#SBATCH -n 1 # tasks
#SBATCH --cpus-per-task 28
#SBATCH --mem=75G

module load singularity/3.8.6
echo "Started with $1: $2, $3"
singularity exec --bind "$2":/data,"$3":/config linefinder.sif /home/flash/FLASH/pipeline/run_linefinder_$1.sh

exit 0
EOT
