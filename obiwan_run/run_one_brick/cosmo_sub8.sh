#!/bin/bash -l   
#SBATCH -p regular
#SBATCH -N 1
#SBATCH -t 00:30:00
#SBATCH --account=desi

#SBATCH -J sub8
#SBATCH -o ./slurm_output/sub8_%j.out
#SBATCH -L SCRATCH,project
#SBATCH -C haswell
#SBATCH --mail-user=kong.291@osu.edu
#SBATCH --mail-type=ALL

export sub_num=8

./slurm_all_subs.sh
