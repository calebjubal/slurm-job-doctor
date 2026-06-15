"""Detect walltime (TIMEOUT) failures."""

from __future__ import annotations

from slurm_job_doctor.diagnosis.context import DiagnosisContext
from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.parsers.unit_parser import format_seconds


def diagnose(ctx: DiagnosisContext) -> list[Diagnosis]:
    job = ctx.job
    logs = ctx.logs

    if not ((job is not None and job.is_timeout) or logs.has("timeout")):
        return []

    evidence: list[str] = []
    if job is not None:
        if job.elapsed_seconds is not None:
            evidence.append(f"Elapsed: {format_seconds(job.elapsed_seconds)}")
        if job.timelimit_seconds is not None:
            evidence.append(f"Time limit: {format_seconds(job.timelimit_seconds)}")
    evidence.extend(f"log: {line}" for line in logs.lines_for("timeout")[:2])

    return [
        Diagnosis(
            code="TIMEOUT",
            category="timeout",
            severity="critical",
            title="Job killed: walltime exceeded",
            message=(
                "The job ran out of walltime before finishing. Increase --time, and add "
                "checkpointing if the runtime is hard to predict."
            ),
            evidence=evidence,
        )
    ]
