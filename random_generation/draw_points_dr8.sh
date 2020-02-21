#!/bin/bash
export name_for_run=SV_south
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/$name_for_run/

python draw_points_dr8.py

rm $obiwan_out/randoms_chunk/randoms_*
