"""Flag CPU cores that were allocated but left idle, including OpenMP mismatches."""

from __future__ import annotations

import re

from slurm_job_doctor.diagnosis.context import DiagnosisContext
from slurm_job_doctor.models.diagnosis import Diagnosis

_OMP_RE = re.compile(r"OMP_NUM_THREADS\s*=\s*(\d+)")


def _to_int(value: str | None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _openmp_mismatch(ctx: DiagnosisContext) -> list[Diagnosis]:
    script = ctx.script
    if script is None:
        return []
    cpus = _to_int(script.cpus_per_task)
    if not cpus or cpus < 2:
        return []
    for line in script.body:
        match = _OMP_RE.search(line)
        if match is not None and int(match.group(1)) == 1:
            return [
                Diagnosis(
                    code="OPENMP_MISMATCH",
                    category="cpu",
                    severity="medium",
                    title="OpenMP thread mismatch",
                    message=(
                        f"--cpus-per-task={cpus} but OMP_NUM_THREADS=1, so up to {cpus - 1} "
                        "cores may sit idle. Set OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1} or "
                        "lower --cpus-per-task."
                    ),
                    evidence=[f"--cpus-per-task={cpus}", "OMP_NUM_THREADS=1"],
                )
            ]
    return []


def diagnose(ctx: DiagnosisContext) -> list[Diagnosis]:
    findings: list[Diagnosis] = []
    job = ctx.job

    if (
        job is not None
        and job.cpu_efficiency is not None
        and job.allocated_cpus
        and job.allocated_cpus > 1
        and job.cpu_efficiency < ctx.config.cpu_efficiency_threshold
    ):
        efficiency = job.cpu_efficiency
        findings.append(
            Diagnosis(
                code="CPU_OVER_REQUESTED",
                category="cpu",
                severity="low",
                title="Low CPU efficiency",
                message=(
                    f"Average CPU efficiency was {efficiency * 100:.0f}% across "
                    f"{job.allocated_cpus} CPUs, so most cores sat idle. Lower "
                    "--cpus-per-task unless the workload is intentionally serial."
                ),
                evidence=[
                    f"Allocated CPUs: {job.allocated_cpus}",
                    f"CPU efficiency: {efficiency * 100:.0f}%",
                ],
            )
        )

    findings.extend(_openmp_mismatch(ctx))
    return findings
