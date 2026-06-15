"""Shared input bundle for the recommenders."""

from __future__ import annotations

from dataclasses import dataclass, field

from slurm_job_doctor.config import DoctorConfig
from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.models.sbatch_script import SbatchScript


@dataclass
class RecommendationContext:
    diagnoses: list[Diagnosis] = field(default_factory=list)
    job: JobRecord | None = None
    script: SbatchScript | None = None
    config: DoctorConfig = field(default_factory=DoctorConfig)

    def has(self, code: str) -> bool:
        return any(diagnosis.code == code for diagnosis in self.diagnoses)
