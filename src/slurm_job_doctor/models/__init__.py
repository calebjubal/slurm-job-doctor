"""Typed data models shared across parsers, diagnosis, and recommenders."""

from slurm_job_doctor.models.sbatch_script import SbatchDirective, SbatchScript

__all__ = ["SbatchDirective", "SbatchScript"]
