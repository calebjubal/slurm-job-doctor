#!/bin/bash
#SBATCH --job-name=infer
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/slurm-%j.out
#SBATCH --error=logs/slurm-%j.err

module load python/3.11
source activate ml
python infer.py --checkpoint model.pt --input batch.jsonl
