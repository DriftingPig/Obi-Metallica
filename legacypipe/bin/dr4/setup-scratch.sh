#! /bin/bash

# Copy input files required for running the Tractor on Edison to $SCRATCH.

# $SCRATCH files older than 12 weeks are purged -- so don't rsync the timestamps!

RSYNC_ARGS="-rlpgo --size-only"

# CP-processed DECam images
mkdir -p $SCRATCH/images
rsync -Riv $RSYNC_ARGS /project/projectdirs/cosmo/staging/./decam/{COSMOS,CP20140810_g_v2,CP20140810_r_v2,CP20140810_z_v2,CP20141227,CP20150108,CP20150326,CP20150407,CPDES82,NonDECaLS/*}/*_oo[idw]_[grz]*.fits* $SCRATCH/images

# Code
# mkdir -p $SCRATCH/code;
# for x in $(ls COPY-TO-SCRATCH); do
#   echo $x;
#   #cp -r COPY-TO-SCRATCH/$x $SCRATCH/code/;
#   rsync -arv COPY-TO-SCRATCH/$x $SCRATCH/code/;
#   ln -s $SCRATCH/code/$x .;
# done

# Calibration products
mkdir -p $SCRATCH/calib/decam
rsync -v $RSYNC_ARGS ~/cosmo/work/decam/calib/{astrom-pv,psfex,sextractor,sky} $SCRATCH/calib/decam

# SDSS photoObj slice
./legacypipe/copy-sdss-slice.py

# unWISE images
mkdir -p $SCRATCH/unwise-coadds
UNW=/project/projectdirs/cosmo/data/unwise/unwise-coadds/
#cp $UNW/allsky-atlas.fits $SCRATCH/unwise-coadds
rsync -Rv $RSYNC_ARGS $UNW/./*/*/*-w{3,4}-{img-m.fits,invvar-m.fits.gz,n-m.fits.gz,n-u.fits.gz} $SCRATCH/unwise-coadds

