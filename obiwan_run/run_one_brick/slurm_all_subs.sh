#!/bin/bash -l



#Note: in slurm_brick_scheduler, RANDOMS_FROM_FITS needs to be changed everytime you start a new run
#note:only rowstart 0/201 are valid, 101 is not valid
export name_for_run=cosmo_sub$sub_num
export randoms_db=None #run from a fits file
export dataset=dr8
export rowstart=0
export do_skipids=no
export do_more=no
export minid=1
export object=elg
export nobj=1

export usecores=64
export threads=$usecores
#threads=1
#obiwan paths
export obiwan_data=$CSCRATCH/Obiwan/dr8/obiwan_data/cosmos_repeats/cosmo_sub$sub_num
export obiwan_code=$CSCRATCH/Obiwan/dr8/obiwan_code 
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/cosmo_subs_all/$name_for_run 

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
srun -N 1 -n 1 -c $usecores shifter --image=driftingpig/obiwan_dr8:step11 ./example1.sh
