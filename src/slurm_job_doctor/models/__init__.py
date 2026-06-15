"""Typed data models shared across parsers, diagnosis, and recommenders."""

from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.models.sbatch_script import SbatchDirective, SbatchScript

__all__ = ["JobRecord", "SbatchDirective", "SbatchScript"]
