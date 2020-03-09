#!/bin/bash -l
export PYTHONPATH=/global/cscratch1/sd/huikong/Obiwan/dr8/obiwan_code/py/:$PYTHONPATH
echo $PYTHONPATH
#python ./example1.py $name_for_run

./slurm_brick_scheduler.sh 1503p015
