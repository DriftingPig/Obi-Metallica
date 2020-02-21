#!/bin/bash
export name_for_run=SV_south
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/$name_for_run/
#tiles for SV
export SV_tiles=$obiwan_out/tiles/

python bricklist_maker.py
