#!/bin/bash
echo entering scheduler...
export LEGACY_SURVEY_DIR=$obiwan_data
RANDOMS_FROM_FITS=$obiwan_out/divided_randoms/brick_${1}.fits

# Burst-buffer!
if [ x$DW_PERSISTENT_STRIPED_DR8 == x ]; then
BB=${LEGACY_SURVEY_DIR}/
else
BB=$DW_PERSISTENT_STRIPED_DR8
fi

#star catalogs
#catdir=/global/cscratch1/sd/landriau/dr8/alldata
export DUST_DIR=/global/project/projectdirs/cosmo/data/dust/v0_0/  #${catdir}/dust_v0.1
export UNWISE_COADDS_DIR=/global/project/projectdirs/cosmo/work/wise/outputs/merge/neo5/fulldepth:/global/project/projectdirs/cosmo/data/unwise/allwise/unwise-coadds/fulldepth #/global/project/projectdirs/cosmo/work/wise/outputs/merge/neo4/fulldepth    #${catdir}/unwise_coadds_4:${catdir}/unwise_coadds_1
export UNWISE_COADDS_TIMERESOLVED_DIR=/global/projecta/projectdirs/cosmo/work/wise/outputs/merge/neo4     #${catdir}/unwise_timeresolved_coadds
export GAIA_CAT_DIR=/global/project/projectdirs/cosmo/work/gaia/chunks-gaia-dr2-astrom-2   #${catdir}/chunks-gaia-dr2-astrom-2
export GAIA_CAT_VER=2
export TYCHO2_KD_DIR=/global/project/projectdirs/cosmo/staging/tycho2    #${catdir}/tycho2
export LARGEGALAXIES_DIR=/global/project/projectdirs/cosmo/staging/largegalaxies/v2.0
UNWISE_PSF_DIR=/src/unwise_psf
export WISE_PSF_DIR=${UNWISE_PSF_DIR}/etc
export PS1CAT_DIR=/global/project/projectdirs/cosmo/work/ps1/cats/chunks-qz-star-v3    #${catdir}/ps1cat

#PYTHONPATH
export PYTHONPATH=$obiwan_code/py:$obiwan_code/legacypipe/py:/usr/local/lib/python:/usr/local/lib/python3.6/dist-packages:.:${UNWISE_PSF_DIR}/py

bri=$(echo ${1} | head -c 3)
outdir=${obiwan_out}/output
if [ ${do_skipids} == "no" ]; then
if [ ${do_more} == "no" ]; then
export rsdir=rs${rowstart}
else
export rsdir=more_rs${rowstart}
fi
else
if [ ${do_more} == "no" ]; then
export rsdir=skip_rs${rowstart}
else
export rsdir=more_skip_rs${rowstart}
fi
fi

# Try limiting memory to avoid killing the whole MPI job...
# 16 is the default for both Edison and Cori: it corresponds
# to 3 and 4 bricks per node respectively.
ncores=16
# 128 GB / Cori Haswell node = 134217728 kbytes
maxmem=134217728
let usemem=${maxmem}*${ncores}/64
ulimit -Sv $usemem
# Reduce the number of cores so that a task doesn't use too much memory.
# Using more threads than the number of physical cores usually causes the
# job to run out of memory.
ncores=8

cd /src/legacypipe/py

#outdir=${BB}decam



log=${outdir}/logs/${bri}/${brick}/${rsdir}/log.$1
mkdir -p $(dirname $log)
echo $dirname
echo logging to...${log}

#log info
echo Running on $(hostname)

echo -e "\n\n\n" >> $log
echo "-----------------------------------------------------------------------------------------" >> $log
echo "PWD: $(pwd)" >> $log
echo >> $log
#echo "Environment:" >> $log
#set | grep -v PASS >> $log
echo >> $log
ulimit -a >> $log
echo >> $log
tmplog="/tmp/$brick.log"

echo -e "\nStarting on $(hostname)\n" >> $log
echo "-----------------------------------------------------------------------------------------" >> $log

export dataset=dr8
threads=32
SLURM_JOB_ID=0

cd 
#echo /global/cscratch1/sd/huikong/obiwan_Aug/repos_for_docker/obiwan_data/DR3_copies/legacysurveydir_dr3_copy${2}${1}
python $obiwan_code/py/kenobi_cosmos.py --dataset ${dataset} -b $1 \
--nobj ${nobj} --rowstart ${rowstart} -o ${object} \
--randoms_db ${randoms_db} --outdir $outdir --add_sim_noise \
--threads $threads \
--do_skipids $do_skipids \
--do_more $do_more --minid $minid \
--randoms_from_fits $RANDOMS_FROM_FITS \
--verbose \
--pickle "${outdir}/pickles/${bri}/${brick}/${rsdir}/runbrick-%(brick)s-%%(stage)s.pickle" \
--all-blobs 
#>> $log 2>&1
#--survey_dir /global/cscratch1/sd/huikong/obiwan_Aug/repos_for_docker/obiwan_data/legacysurveydir_dr3/
