#!/bin/bash
export name_for_run=SV_south
#copy if it's the first time
#cp ../../obiwan_out/SV_south/bricklist.txt ./real_brick_lists/$name_for_run.txt
export obiwan_out=$CSCRATCH/Obiwan/dr8/$name_for_run

python brickstat.py --name_for_run $name_for_run --rs rs1 --real_bricks_fn $name_for_run.txt


