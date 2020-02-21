#!/bin/bash -l
#source /srv/py3_venv/bin/activate
export PYTHONPATH=/global/cscratch1/sd/huikong/Obiwan/dr8/obiwan_code:$PYTHONPATH

python ./example1.py $name_for_run
