#!/bin/bash -l

#SBATCH -p debug
#SBATCH -N 1 
#SBATCH -t 00:05:00
#SBATCH --account=desi
#SBATCH -J deepELG
#SBATCH --mail-user=kburleigh@lbl.gov
#SBATCH --mail-type=END,FAIL
#SBATCH -L SCRATCH

#-- -C haswell
#--qos=premium
#--array=1-20

export OMP_NUM_THREADS=1

# Yu Feng's bcast
#source /scratch1/scratchdirs/desiproc/DRs/code/dr4/yu-bcast_2/activate.sh
module load mpi4py-hpcp/2.0.0_70f79779-9.0

#export runwhat=star
#export runwhat=qso
export runwhat=elg
#export runwhat=lrg


export nobj=400
export rowstart=0

export LEGACY_SURVEY_DIR=/global/cscratch1/sd/kaylanb/dr3-obiwan/legacypipe-dir
#export DECALS_SIM_DIR=/global/cscratch1/sd/kaylanb/dr3-obiwan/deeptraining
#export DECALS_SIM_DIR=/global/cscratch1/sd/kaylanb/dr3-obiwan/galaxies_starflux
export DECALS_SIM_DIR=/global/cscratch1/sd/kaylanb/dr3-obiwan/galaxies_starflux_re0.5
export outdir=$DECALS_SIM_DIR

# Put legacypipe in path
export PYTHONPATH=.:${PYTHONPATH}

if [ "$NERSC_HOST" == "cori" ]; then
    cores=32
elif [ "$NERSC_HOST" == "edison" ]; then
    cores=24
fi
let tasks=${SLURM_JOB_NUM_NODES}*${cores}

threads=1
export OMP_NUM_THREADS=$threads
export MKL_NUM_THREADS=1

export therun=eboss-ngc
export prefix=eboss_ngc
bricklist=bricks-eboss-ngc.txt
date
## Decals_sim.py
srun -n $tasks python obiwan/decals_sim_mpiwrapper.py \
    --nproc $tasks --bricklist $bricklist \
    --run $therun --objtype $runwhat --brick None --rowstart $rowstart \
    --nobj $nobj \
    --add_sim_noise --prefix $prefix --threads $OMP_NUM_THREADS \
    --cutouts --bright_galaxies 
## Gather_cutouts.py
#srun -n $tasks python obiwan/gather_cutouts_mpiwrapper.py --nproc $tasks
# Serial concatenation of hdf5 products
#srun -n 1 -c 24 python obiwan/gather_cutouts.py
date

