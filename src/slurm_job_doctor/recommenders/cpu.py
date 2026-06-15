"""Recommend CPU-count changes and OpenMP fixes."""

from __future__ import annotations

import math

from slurm_job_doctor.models.recommendation import Recommendation
from slurm_job_doctor.recommenders.context import RecommendationContext
from slurm_job_doctor.recommenders.util import to_int


def recommend(ctx: RecommendationContext) -> list[Recommendation]:
    job = ctx.job
    findings: list[Recommendation] = []

    if (
        ctx.has("CPU_OVER_REQUESTED")
        and job is not None
        and job.allocated_cpus
        and job.elapsed_seconds
        and job.total_cpu_seconds is not None
    ):
        busy = job.total_cpu_seconds / job.elapsed_seconds
        new_cpus = max(1, math.ceil(busy))
        current = (to_int(ctx.script.cpus_per_task) if ctx.script else None) or job.allocated_cpus
        if new_cpus < current:
            findings.append(
                Recommendation(
                    directive="--cpus-per-task",
                    old_value=str(current),
                    new_value=str(new_cpus),
                    reason=f"Only ~{busy:.1f} of {current} cores were busy on average.",
                )
            )

    if ctx.has("OPENMP_MISMATCH"):
        findings.append(
            Recommendation(
                directive="OMP_NUM_THREADS",
                old_value="1",
                new_value="${SLURM_CPUS_PER_TASK:-1}",
                reason="Bind OpenMP threads to the CPU allocation instead of a single thread.",
                kind="script",
            )
        )

    return findings
