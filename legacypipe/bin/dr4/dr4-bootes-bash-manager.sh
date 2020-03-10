#!/bin/bash

# Run: bash dr4-bootes-bash-manager.sh 90prime; bash dr4-bootes-bash-manager.sh mzlsv2thruMarch19
#export camera="$1"
#if [ "$camera" = "90prime" ] || [ "$camera" = "mzlsv2thruMarch19" ] ; then
#    echo Script running
#else
#    echo Crashing
#    exit
#fi

export run_name=dr4-bootes
export outdir=/scratch1/scratchdirs/desiproc/DRs/data-releases/dr4-bootes/90primeTPV_mzlsv2thruMarch19/wisepsf_bash
export statdir="${outdir}/progress"
mkdir -p $statdir $outdir

# Clean up
for i in `find . -maxdepth 1 -type f -name "dr4-bootes.o*"|xargs grep "${run_name} DONE"|cut -d ' ' -f 3|grep "^[0-9]*[0-9]$"`; do mv dr4-bootes.o$i $outdir/logs/;done

# Cancel ALL jobs and remove all inq.txt files
#for i in `squeue -u desiproc|grep dr3-mzls-b|cut -c10-18`; do scancel $i;done
#rm /scratch1/scratchdirs/desiproc/data-releases/dr3-mzls-bash/progress/*.txt

# Submit jobs
#bricklist=$LEGACY_SURVEY_DIR/bricks-bothcameras.txt
bricklist=bootesbricks.txt
if [ ! -e "$bricklist" ]; then
    echo file=$bricklist does not exist, quitting
    exit 999
fi

#for brick in `cat bootesbricks.txt`;do
for brick in `cat $bricklist`;do
    export brick="$brick"
    bri=$(echo $brick | head -c 3)
    tractor_fits=$outdir/tractor/$bri/tractor-$brick.fits
    if [ -e "$tractor_fits" ]; then
        echo skipping $brick, its done
        # Remove coadd, checkpoint, pickle files they are huge
        rm $outdir/pickles/${bri}/runbrick-${brick}*.pickle
        rm $outdir/checkpoints/${bri}/${brick}*.pickle
        #rm $outdir/coadd/${bri}/${brick}/*
    elif [ -e "$statdir/inq_$brick.txt" ]; then
        echo skipping $brick, its queued
    else
        echo nothing
        echo submitting $brick
        touch $statdir/inq_$brick.txt
        sbatch dr4-bootes-bash.sh --export outdir,statdir,brick,run_name
    fi
done
