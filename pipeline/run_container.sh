#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_slurm_scripts.sh", which calls:
#                   2) "run_container.sh", which calls:
#                       3) a singularity container running "run_linefinder.sh"
#
######################################################################################
######################################################################################

sbatch <<EOT
#!/bin/bash
#SBATCH --job-name=flashfinder
#SBATCH --output="$1"/outputs/logs/finder_output_%j.log
#SBATCH --error="$1"/outputs/logs/finder_error_%j.log
#SBATCH -N 1 # nodes
#SBATCH -n 1 # tasks
#SBATCH --cpus-per-task 28
#SBATCH --mem=75G

module load singularity/3.8.6
mkdir -p "$1"/outputs/logs
echo "Started with $1: $2"
singularity exec --bind "$1":/data,"$2":/config linefinder.sif /home/flash/FLASH/pipeline/run_linefinder.sh

exit 0
EOT
