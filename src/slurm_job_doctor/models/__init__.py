"""Typed data models shared across parsers, diagnosis, and recommenders."""

from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.models.log_evidence import LogEvidence, LogMatch
from slurm_job_doctor.models.sbatch_script import SbatchDirective, SbatchScript

__all__ = [
    "Diagnosis",
    "JobRecord",
    "LogEvidence",
    "LogMatch",
    "SbatchDirective",
    "SbatchScript",
]
