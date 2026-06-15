"""Run every diagnosis rule and return a de-duplicated, severity-ordered list."""

from __future__ import annotations

from collections.abc import Callable

from slurm_job_doctor.config import DoctorConfig
from slurm_job_doctor.diagnosis import (
    cpu_efficiency,
    environment,
    gpu,
    memory_efficiency,
    oom,
    state,
    timeout,
)
from slurm_job_doctor.diagnosis.context import DiagnosisContext
from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.models.log_evidence import LogEvidence
from slurm_job_doctor.models.sbatch_script import SbatchScript

# Order matters only for stability among equal-severity findings: failures first.
_RULES: list[Callable[[DiagnosisContext], list[Diagnosis]]] = [
    oom.diagnose,
    timeout.diagnose,
    state.diagnose,
    environment.diagnose,
    gpu.diagnose,
    memory_efficiency.diagnose,
    cpu_efficiency.diagnose,
]


def diagnose(
    job: JobRecord | None = None,
    script: SbatchScript | None = None,
    logs: LogEvidence | None = None,
    *,
    config: DoctorConfig | None = None,
    log_text: str | None = None,
) -> list[Diagnosis]:
    """Diagnose a job from whatever evidence is available.

    Returns findings sorted by severity (most serious first). Each diagnosis code
    appears at most once, keeping the highest-severity instance.
    """
    ctx = DiagnosisContext(
        job=job,
        script=script,
        logs=logs if logs is not None else LogEvidence(),
        config=config or DoctorConfig(),
        log_text=log_text,
    )

    findings: list[Diagnosis] = []
    for rule in _RULES:
        findings.extend(rule(ctx))

    by_code: dict[str, Diagnosis] = {}
    for finding in findings:
        existing = by_code.get(finding.code)
        if existing is None or finding.rank > existing.rank:
            by_code[finding.code] = finding

    return sorted(by_code.values(), key=lambda d: d.rank, reverse=True)


def primary(diagnoses: list[Diagnosis]) -> Diagnosis | None:
    """Return the most serious diagnosis, or None when the list is empty."""
    return diagnoses[0] if diagnoses else None
