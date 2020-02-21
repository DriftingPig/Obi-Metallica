#!/bin/bash -l

#SBATCH -q debug
#SBATCH -N 10
#SBATCH -t 00:30:00
#SBATCH --account=desi
#SBATCH -J ran_division
#SBATCH -L SCRATCH,project
#SBATCH -C haswell
#SBATCH --mail-user=kong.291@osu.edu
#SBATCH --mail-type=ALL

export name_for_run=SV_south
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/$name_for_run
export obiwan_data=$CSCRATCH/Obiwan/dr8/obiwan_data/legacysurveydir_dr8/
export NODE_NUM=10 #this should be consistent with the number of nodes you request

#NERSC things
export KMP_AFFINITY=disabled
export MPICH_GNI_FORK_MODE=FULLCOPY
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
# Protect against astropy configs
export XDG_CONFIG_HOME=/dev/shm
#srun -n $SLURM_JOB_NUM_NODES mkdir -p $XDG_CONFIG_HOME/astropy

upper_lim=$(( NODE_NUM - 1 ))

for (( i=0; i<upper_lim; i++ ))
do
	srun -n 1 -c 64 python GetBricksSrc_SV.py $i &
done

srun -n 1 -c 64 python GetBricksSrc_SV.py $upper_lim 

wait


