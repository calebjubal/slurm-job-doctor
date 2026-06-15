"""Bundle of inputs shared by every diagnosis rule."""

from __future__ import annotations

from dataclasses import dataclass, field

from slurm_job_doctor.config import DoctorConfig
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.models.log_evidence import LogEvidence
from slurm_job_doctor.models.sbatch_script import SbatchScript


@dataclass
class DiagnosisContext:
    job: JobRecord | None = None
    script: SbatchScript | None = None
    logs: LogEvidence = field(default_factory=LogEvidence)
    config: DoctorConfig = field(default_factory=DoctorConfig)
    log_text: str | None = None  # concatenated stdout/stderr, when available

    @property
    def has_logs(self) -> bool:
        return self.log_text is not None
