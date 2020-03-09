#!/bin/bash
export name_for_run=cosmos_repeat
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/$name_for_run
export obiwan_data=$CSCRATCH/Obiwan/dr8/obiwan_data/legacysurveydir_dr8/
#for name_for_run=SV_sounth only
export export SV_tiles=$obiwan_out/tiles/

python radec_maker.py
