"""Recommend memory changes from memory-related diagnoses."""

from __future__ import annotations

from slurm_job_doctor.models.recommendation import Recommendation
from slurm_job_doctor.parsers.unit_parser import format_memory_mb
from slurm_job_doctor.recommenders.context import RecommendationContext
from slurm_job_doctor.recommenders.util import (
    cap_memory,
    current_memory_mb,
    round_up_gb,
    to_int,
)

# Trim over-requested memory to peak RSS times this factor (README's memory-waste rule).
_TRIM_FACTOR = 1.3


def _memory_recommendation(
    ctx: RecommendationContext, target_total_mb: int, reason: str
) -> Recommendation:
    """Build a memory recommendation that matches how the script expresses memory.

    If the script uses ``--mem-per-cpu`` (and not ``--mem``), target that directive so the
    patched script does not end up with both ``--mem`` and ``--mem-per-cpu``, which Slurm
    rejects as mutually exclusive.
    """
    script = ctx.script
    uses_per_cpu = script is not None and bool(script.mem_per_cpu) and not script.mem
    if uses_per_cpu:
        cpus = to_int(script.cpus_per_task)
        if not cpus and ctx.job is not None:
            cpus = ctx.job.allocated_cpus
        cpus = cpus or 1
        per_cpu_mb = round_up_gb(target_total_mb / cpus)
        return Recommendation(
            directive="--mem-per-cpu",
            old_value=script.mem_per_cpu,
            new_value=format_memory_mb(per_cpu_mb),
            reason=reason,
        )

    _, current_display = current_memory_mb(ctx)
    return Recommendation(
        directive="--mem",
        old_value=current_display,
        new_value=format_memory_mb(target_total_mb),
        reason=reason,
    )


def recommend(ctx: RecommendationContext) -> list[Recommendation]:
    job = ctx.job
    config = ctx.config
    current_mb, _ = current_memory_mb(ctx)
    findings: list[Recommendation] = []

    if ctx.has("OUT_OF_MEMORY"):
        candidates: list[float] = []
        if job is not None and job.max_rss_mb:
            candidates.append(job.max_rss_mb * config.oom_memory_growth_factor)
        if current_mb:
            candidates.append(current_mb * config.min_memory_safety_factor)
        if candidates:
            target = round_up_gb(max(candidates))
            if current_mb:  # always end strictly above the current request
                target = max(target, round_up_gb(current_mb + 1))
            target = cap_memory(target, config)
            findings.append(
                _memory_recommendation(
                    ctx,
                    target,
                    "Job was killed at the memory limit; sized to peak RSS × "
                    f"{config.oom_memory_growth_factor:g} with headroom.",
                )
            )
    elif ctx.has("MEMORY_OVER_REQUESTED") and job is not None and job.max_rss_mb:
        target = round_up_gb(job.max_rss_mb * _TRIM_FACTOR)
        if current_mb and target < current_mb:
            util = job.memory_utilization or 0.0
            findings.append(
                _memory_recommendation(
                    ctx,
                    target,
                    f"Only {util * 100:.0f}% of memory was used; trimmed to peak RSS × "
                    f"{_TRIM_FACTOR:g} to shorten queue time.",
                )
            )
    elif ctx.has("MEMORY_NEAR_LIMIT") and job is not None and job.max_rss_mb:
        target = round_up_gb(max(job.max_rss_mb * 1.2, (current_mb or 0) * 1.15))
        if current_mb and target > current_mb:
            target = cap_memory(target, config)
            findings.append(
                _memory_recommendation(
                    ctx,
                    target,
                    "Peaked near the limit; added headroom to avoid a future OOM.",
                )
            )

    if ctx.has("CUDA_OUT_OF_MEMORY"):
        findings.append(
            Recommendation(
                kind="note",
                reason=(
                    "GPU out of memory: reduce batch size or use gradient "
                    "accumulation/checkpointing. --mem controls host RAM, not GPU memory."
                ),
            )
        )

    return findings
