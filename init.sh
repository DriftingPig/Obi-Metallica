#!/bin/bash

#change the run name here
export name_for_run=dr8_SV
export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/$name_for_run 
#export obiwan_out=$CSCRATCH/Obiwan/dr8/obiwan_out/cosmo_subs_all/$name_for_run 
mkdir $obiwan_out
mkdir $obiwan_out/divided_randoms
mkdir $obiwan_out/output
mkdir $obiwan_out/randoms_chunk
