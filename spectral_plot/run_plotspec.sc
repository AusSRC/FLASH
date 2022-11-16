#!/bin/bash -l
#SBATCH --time=12:00:00
#SBATCH --ntasks=1
#SBATCH --ntasks-per-node=1
#SBATCH --job-name=plot_spec
#SBATCH --no-requeue
#SBATCH --export=NONE
##SBATCH --account=ja3
##SBATCH --partition=debugq

module use /group/askap/modulefiles
#module swap PrgEnv-cray/6.0.4 PrgEnv-gnu/6.0.4
#module load askappy
module load python
module load numpy
module load scipy
module load astropy
module load matplotlib
#module load askappy

export MPICH_GNI_MALLOC_FALLBACK=enabled

#srun --export=ALL python ./plot_spec_pawsey.py --sbid=11068 
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13293 
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13294 
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13306 
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=10850
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=11051 
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=11052 
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=11053
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13268 
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13269 
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13270 
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13271
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13272
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13273
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13278
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13279
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13281
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13283
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13284
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13285
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13290
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13291
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13296
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13297
srun --export=ALL python ./plot_spec_pawsey.py --sbid=13298
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13299
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13305
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13334
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13335
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13336
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=13372
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=15208
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=15209
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=15212
#srun --export=ALL python ./plot_spec_pawsey.py --sbid=15873
