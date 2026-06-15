#!/bin/bash
#SBATCH --job-name=montecarlo
#SBATCH --partition=compute
#SBATCH --cpus-per-task=16
#SBATCH --mem=8G
#SBATCH --time=04:00:00
#SBATCH --output=logs/slurm-%j.out
#SBATCH --error=logs/slurm-%j.err

module load python/3.11
source activate ml
# single-process simulation: only one core is ever busy
python montecarlo.py --samples 50000000
