"""Recommend walltime changes from timeout diagnoses (or obvious over-requests)."""

from __future__ import annotations

from slurm_job_doctor.models.recommendation import Recommendation
from slurm_job_doctor.parsers.unit_parser import format_seconds
from slurm_job_doctor.recommenders.context import RecommendationContext
from slurm_job_doctor.recommenders.util import (
    cap_time,
    current_time_seconds,
    round_up_minute,
)

# Only suggest trimming walltime when a completed job used less than this fraction of it.
_OVER_REQUEST_RATIO = 0.4


def recommend(ctx: RecommendationContext) -> list[Recommendation]:
    job = ctx.job
    config = ctx.config
    current_s, current_display = current_time_seconds(ctx)
    findings: list[Recommendation] = []

    if ctx.has("TIMEOUT"):
        base = job.elapsed_seconds if (job and job.elapsed_seconds) else current_s
        if base:
            target = round_up_minute(base * config.timeout_safety_factor)
            if current_s:
                target = max(target, current_s + 60)
            target = cap_time(target, config)
            findings.append(
                Recommendation(
                    directive="--time",
                    old_value=current_display,
                    new_value=format_seconds(target),
                    reason=(
                        "Job hit its walltime; sized to elapsed × "
                        f"{config.timeout_safety_factor:g}."
                    ),
                )
            )
            findings.append(
                Recommendation(
                    kind="note",
                    reason="Add checkpointing so a long run can resume after a timeout.",
                )
            )
    elif (
        job is not None
        and not job.is_failed
        and job.elapsed_seconds
        and current_s
        and job.elapsed_seconds < _OVER_REQUEST_RATIO * current_s
    ):
        target = round_up_minute(job.elapsed_seconds * config.timeout_safety_factor)
        if target < current_s:
            findings.append(
                Recommendation(
                    directive="--time",
                    old_value=current_display,
                    new_value=format_seconds(target),
                    reason=(
                        "Used a small fraction of the walltime; trimming can cut queue time."
                    ),
                )
            )

    return findings
