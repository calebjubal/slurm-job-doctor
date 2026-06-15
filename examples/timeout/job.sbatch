#!/bin/bash
#SBATCH --job-name=train_lstm
#SBATCH --partition=compute
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=logs/slurm-%j.out
#SBATCH --error=logs/slurm-%j.err

module load python/3.11
source activate ml
python train.py --model lstm --epochs 20
