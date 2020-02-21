#!/bin/bash
export name_for_run=test
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/$name_for_run/
export seed_truth=/global/cscratch1/sd/raichoor/desi_mcsyst/desi_mcsyst_truth.dr7.34ra38.-7dec-3.fits

python seed_formation.py

python rhalf_hist_maker.py

rm $obiwan_out/elg_like.fits
