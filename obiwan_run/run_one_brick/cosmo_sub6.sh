#!/bin/bash -l   
#SBATCH -p regular
#SBATCH -N 1
#SBATCH -t 00:30:00
#SBATCH --account=desi

#SBATCH -J sub6
#SBATCH -o ./slurm_output/sub6_%j.out
#SBATCH -L SCRATCH,project
#SBATCH -C haswell
#SBATCH --mail-user=kong.291@osu.edu
#SBATCH --mail-type=ALL

export sub_num=6

./slurm_all_subs.sh
