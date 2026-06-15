"""Flag memory that was over-requested or uncomfortably close to the limit."""

from __future__ import annotations

from slurm_job_doctor.diagnosis.context import DiagnosisContext
from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.parsers.unit_parser import format_memory_mb


def diagnose(ctx: DiagnosisContext) -> list[Diagnosis]:
    job = ctx.job
    if job is None or job.is_oom:
        # Never suggest lowering memory after an OOM.
        return []

    utilization = job.memory_utilization
    if utilization is None:
        return []

    evidence = [
        f"Requested memory: {format_memory_mb(job.requested_memory_mb)}",
        f"Max RSS: {format_memory_mb(job.max_rss_mb)}",
        f"Utilization: {utilization * 100:.0f}%",
    ]

    if utilization < ctx.config.memory_overrequest_ratio:
        return [
            Diagnosis(
                code="MEMORY_OVER_REQUESTED",
                category="memory",
                severity="low",
                title="Memory over-requested",
                message=(
                    f"The job used only {utilization * 100:.0f}% of its requested memory. "
                    "Requesting less can shorten queue time without risking an OOM."
                ),
                evidence=evidence,
            )
        ]

    if utilization >= ctx.config.memory_near_limit_ratio:
        return [
            Diagnosis(
                code="MEMORY_NEAR_LIMIT",
                category="memory",
                severity="medium",
                title="Memory close to the limit",
                message=(
                    f"The job peaked at {utilization * 100:.0f}% of requested memory. It "
                    "finished, but a slightly larger input could trigger an OOM. Consider a "
                    "small memory headroom."
                ),
                evidence=evidence,
            )
        ]

    return []
