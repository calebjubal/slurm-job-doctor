"""Safely rewrite sbatch scripts from recommendations."""

from slurm_job_doctor.patcher.sbatch_patcher import PatchResult, patch_file, patch_text

__all__ = ["PatchResult", "patch_file", "patch_text"]
