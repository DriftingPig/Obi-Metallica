#!/bin/bash -l

#SBATCH -p shared
#SBATCH -n 8
#SBATCH -t 00:10:00
#SBATCH --account=desi
#SBATCH -J OBILRG
#SBATCH --mail-user=kburleigh@lbl.gov
#SBATCH --mail-type=END,FAIL
#SBATCH -L SCRATCH
#SBATCH -C haswell

#--array=1-2
#--qos=scavenger


#export runwhat=star
#export runwhat=qso
#export runwhat=elg
export runwhat=lrg

if [ "$runwhat" = "star" ]; then
    export nobj=500
elif [ "$runwhat" = "qso" ]; then
    export nobj=500
elif [ "$runwhat" = "elg" ]; then
    export nobj=100
elif [ "$runwhat" = "lrg" ]; then
    export nobj=100
else
    echo runwhat=$runwhat not supported
    exit
fi

usecores=4
threads=$usecores
# Limit memory to avoid 1 srun killing whole node
if [ "$NERSC_HOST" = "edison" ]; then
    # 62 GB / Edison node = 65000000 kbytes
    maxmem=65000000
    let usemem=${maxmem}*${usecores}/24
else
    # 128 GB / Edison node = 65000000 kbytes
    maxmem=134000000
    let usemem=${maxmem}*${usecores}/32
fi
ulimit -S -v $usemem
ulimit -a

echo usecores=$usecores
echo threads=$threads



#bcast
#source /scratch1/scratchdirs/desiproc/DRs/code/dr4/yu-bcast_2/activate.sh


# DR4
#export outdir=/scratch1/scratchdirs/desiproc/DRs/data-releases/dr4
#export outdir=/scratch2/scratchdirs/kaylanb/dr4
export outdir=$DECALS_SIM_DIR

# Override Use dr4 legacypipe-dr
#export LEGACY_SURVEY_DIR=/scratch1/scratchdirs/desiproc/DRs/dr4-bootes/legacypipe-dir

export PYTHONPATH=$CODE_DIR/legacypipe/py:${PYTHONPATH}
cd $CODE_DIR/legacypipe/py

########## GET OBJTYPE, BRICK, ROWSTART
export statdir="${outdir}/progress"
mkdir -p $statdir $outdir

export OMP_NUM_THREADS=$threads

# Force MKL single-threaded
# https://software.intel.com/en-us/articles/using-threaded-intel-mkl-in-multi-thread-application
export MKL_NUM_THREADS=1

while true; do
    echo GETTING BRICK
    date
    bricklist=${LEGACY_SURVEY_DIR}/eboss-ngc-load-${runwhat}-${NERSC_HOST}.txt
    if [ ! -e "$bricklist" ]; then
        echo file=$bricklist does not exist, quitting
        exit 999
    fi
    # Start at random line, avoids running same brick
    lns=`wc -l $bricklist |awk '{print $1}'`
    rand=`echo $((1 + RANDOM % $lns))`
    # Use <<< to prevent loop from being subprocess where variables get lost
    while read aline; do
        objtype=`echo $aline|awk '{print $1}'`
        brick=`echo $aline|awk '{print $2}'`
        rowstart=`echo $aline|awk '{print $3}'`
        # Check whether to skip it
        bri=$(echo $brick | head -c 3)
        tractor_fits="${outdir}/${objtype}/${bri}/${brick}/rowstart${rowstart}/tractor-${objtype}-${brick}-rowstart${rowstart}.fits"
        exceed_rows="${outdir}/${objtype}/${bri}/${brick}/rowstart${rowstart}_exceeded.txt"
        inq=$statdir/inq_${objtype}_${brick}_${rowstart}.txt
        if [ -e "$tractor_fits" ]; then
            continue
        elif [ -e "$exceed_rows" ]; then
            continue
        elif [ -e "$inq" ]; then
            continue
        else
            # Found something to run
            #export objtype="$objtype"
            #export brick="$brick"
            #export rowstart="$rowstart"
            touch $inq
            break
        fi
    done <<< "$(sed -n ${rand},${lns}p $bricklist)"

    echo FOUND BRICK: $inq
    date
    ################

    #export outdir=/scratch1/scratchdirs/desiproc/DRs/data-releases/dr4-bootes/90primeTPV_mzlsv2thruMarch19/wisepsf
    #qdo_table=dr4-bootes

    set -x
    log="$outdir/$objtype/$bri/$brick/logs/log.rowst${rowstart}_${SLURM_JOB_ID}_${SLURM_ARRAY_TASK_ID}"
    mkdir -p $(dirname $log)
    echo Logging to: $log
    echo "-----------------------------------------------------------------------------------------" >> $log
    #module load psfex-hpcp
    export therun=eboss-ngc
    export prefix=eboss_ngc
    date
    srun -n 1 -c $usecores python obiwan/decals_sim.py \
        --run $therun --objtype $objtype --brick $brick --rowstart $rowstart \
        --nobj $nobj \
        --add_sim_noise --prefix $prefix --threads $OMP_NUM_THREADS \
        >> $log 2>&1 &
    wait
    date
    rm ${inq}
    set +x
done
# Bootes
#--run dr4-bootes \

#--no-wise \
#--zoom 1400 1600 1400 1600
#rm $statdir/inq_$brick.txt

#     --radec $ra $dec
#    --force-all --no-write \
#    --skip-calibs \
#
echo obiwan-${runwhat} DONE 

# 
# qdo launch DR4 100 --cores_per_worker 24 --batchqueue regular --walltime 00:55:00 --script ./dr4-qdo.sh --keep_env --batchopts "-a 0-11"
# qdo launch DR4 300 --cores_per_worker 8 --batchqueue regular --walltime 00:55:00 --script ./dr4-qdo-threads8 --keep_env --batchopts "-a 0-11"
# qdo launch DR4 300 --cores_per_worker 8 --batchqueue regular --walltime 00:55:00 --script ./dr4-qdo-threads8-vunlimited.sh --keep_env --batchopts "-a 0-5"

#qdo launch mzlsv2_bcast 4 --cores_per_worker 6 --batchqueue debug --walltime 00:10:00 --script ./dr4-qdo.sh --keep_env
# MPI no bcast
#qdo launch mzlsv2 2500 --cores_per_worker 6 --batchqueue regular --walltime 01:00:00 --script ./dr4-qdo.sh --keep_env
# MPI w/ bcast
#uncomment bcast line in: /scratch1/scratchdirs/desiproc/DRs/code/dr4/qdo/qdo/etc/qdojob
#qdo launch mzlsv2_bcast 2500 --cores_per_worker 6 --batchqueue regular --walltime 01:00:00 --script ./dr4-qdo.sh --keep_env

#qdo launch dr4Bootes2 100 --cores_per_worker 24 --batchqueue debug --walltime 00:30:00 --script ./dr4-bootes-qdo.sh --keep_env
#qdo launch dr4Bootes2 8 --cores_per_worker 24 --batchqueue regular --walltime 01:00:00 --script ./dr4-bootes-qdo.sh --keep_env --batchopts "--qos=premium"
# qdo launch dr2n 16 --cores_per_worker 8 --walltime=24:00:00 --script ../bin/pipebrick.sh --batchqueue regular --verbose
# qdo launch edr0 4 --cores_per_worker 8 --batchqueue regular --walltime 4:00:00 --script ../bin/pipebrick.sh --keep_env --batchopts "--qos=premium -a 0-3"
