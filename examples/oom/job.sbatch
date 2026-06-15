#!/bin/bash
#SBATCH --job-name=preprocess
#SBATCH --partition=compute
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=02:00:00
#SBATCH --output=logs/slurm-%j.out
#SBATCH --error=logs/slurm-%j.err

module load python/3.11
source activate ml
python preprocess.py --dataset big_corpus
