#!/bin/bash
export name_for_run=cosmo_subs_all
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/$name_for_run/
mkdir $obiwan_out
#tiles for SV
export SV_tiles=$obiwan_out/tiles/

python bricklist_maker.py
