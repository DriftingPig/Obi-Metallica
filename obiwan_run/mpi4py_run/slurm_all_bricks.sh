#!/bin/bash -l

#SBATCH -p debug
#SBATCH -N 5
#SBATCH -t 00:30:00
#SBATCH --account=desi
###SBATCH --image=driftingpig/obiwan_dr8:step11
#SBATCH -J obiwan
#SBATCH -o ./slurm_output/SV_south_%j.out
#SBATCH -L SCRATCH,project
#SBATCH -C haswell
#SBATCH --mail-user=kong.291@osu.edu  
#SBATCH --mail-type=ALL


#Note: in slurm_brick_scheduler, RANDOMS_FROM_FITS needs to be changed everytime you start a new run
#note:only rowstart 0/201 are valid, 101 is not valid
export name_for_run=dr8_SV
export randoms_db=None #run from a fits file
export dataset=dr8
export rowstart=0
export do_skipids=no
export do_more=no
export minid=1
export object=elg
export nobj=200

export usecores=32
export threads=$usecores
#threads=1
#obiwan paths
export obiwan_data=$CSCRATCH/Obiwan/dr8/obiwan_data/legacysurveydir_dr8/
export obiwan_code=$CSCRATCH/Obiwan/dr8/obiwan_code 
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/$name_for_run

# Load production env
#source $CSCRATCH/obiwan_code/obiwan/bin/run_atnersc/bashrc_obiwan

# NERSC / Cray / Cori / Cori KNL things
export KMP_AFFINITY=disabled
export MPICH_GNI_FORK_MODE=FULLCOPY
export MKL_NUM_THREADS=1
export OMP_NUM_THREADS=1
# Protect against astropy configs
export XDG_CONFIG_HOME=/dev/shm
srun -n $SLURM_JOB_NUM_NODES mkdir -p $XDG_CONFIG_HOME/astropy
echo entering srun
srun -N 5 -n 10 -c $usecores shifter --image=driftingpig/obiwan_dr8:step11 ./example1.sh
wait
