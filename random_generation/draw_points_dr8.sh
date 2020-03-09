#!/bin/bash
export name_for_run=cosmos_repeat
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/$name_for_run/
export TOTAL_POINTS=5000000
#mkdir $obiwan_out
mkdir $obiwan_out/randoms_chunk
python draw_points_dr8.py

rm $obiwan_out/randoms_chunk/randoms_*
