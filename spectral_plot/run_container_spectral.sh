#!/bin/bash
######################################################################################
######################################################################################
#   NOTE:   The script calling order is:
#               1) "run_slurm_spectral.sh", which calls:
#                   2) "run_container_spectral.sh", which calls:
#                       3) a singularity container running "run_spectrals.sh"
#
######################################################################################
######################################################################################

sbatch <<EOT
#!/bin/bash
#SBATCH --job-name=spectral_plot
#SBATCH --output="$1/$2"/spectra_ascii/logs/finder_output_%j.log
#SBATCH --error="$1/$2"/spectra_ascii/logs/finder_error_%j.log
#SBATCH -N 1 # nodes
#SBATCH -n 1 # tasks
#SBATCH --cpus-per-task 32
#SBATCH --mem=75G

module load singularity/3.8.6
mkdir -p "$1/$2"/spectra_ascii/logs
echo "Started with $1: $2 $3"
singularity exec --bind "$1":/data,"$3":/config spectral_plot.sif /home/flash/FLASH/spectral_plot/run_spectrals.sh $2

exit 0
EOT