"""Estimate the queue-time cost of recommended resource changes.

Bigger memory and longer walltime usually mean a longer queue wait, so the tool offers
a "Recommended" option and, after a hard failure, a more cautious "Conservative" one,
each labelled with a rough success probability and queue impact.
"""

from __future__ import annotations

from slurm_job_doctor.models.recommendation import Recommendation, ResourceOption
from slurm_job_doctor.parsers.unit_parser import (
    format_memory_mb,
    format_seconds,
    parse_memory_mb,
    parse_time_seconds,
)
from slurm_job_doctor.recommenders.context import RecommendationContext
from slurm_job_doctor.recommenders.util import (
    current_memory_mb,
    current_time_seconds,
    round_up_gb,
    round_up_minute,
)

_IMPACT_LABELS = ["low", "medium", "high", "high"]


def _ratio_bucket(old: int | None, new: int | None) -> int:
    if not old or not new or new <= old:
        return 0
    ratio = new / old
    if ratio <= 1.1:
        return 0
    if ratio <= 1.6:
        return 1
    if ratio <= 2.5:
        return 2
    return 3


def _impact(
    old_mem: int | None,
    new_mem: int | None,
    old_time: int | None,
    new_time: int | None,
) -> str:
    bucket = max(_ratio_bucket(old_mem, new_mem), _ratio_bucket(old_time, new_time))
    return _IMPACT_LABELS[bucket]


def estimate(
    ctx: RecommendationContext, recommendations: list[Recommendation]
) -> list[ResourceOption]:
    current_mem, _ = current_memory_mb(ctx)
    current_time, _ = current_time_seconds(ctx)

    mem_rec = next((r for r in recommendations if r.directive == "--mem"), None)
    time_rec = next((r for r in recommendations if r.directive == "--time"), None)
    rec_mem = current_mem
    if mem_rec and mem_rec.new_value:
        rec_mem = parse_memory_mb(mem_rec.new_value)
    rec_time = current_time
    if time_rec and time_rec.new_value:
        rec_time = parse_time_seconds(time_rec.new_value)

    options = [
        ResourceOption(
            label="Recommended",
            mem=format_memory_mb(rec_mem) if rec_mem else None,
            time=format_seconds(rec_time) if rec_time else None,
            success_probability="high",
            queue_impact=_impact(current_mem, rec_mem, current_time, rec_time),
        )
    ]

    if ctx.has("OUT_OF_MEMORY") or ctx.has("TIMEOUT"):
        cons_mem = rec_mem
        cons_time = rec_time
        if ctx.has("OUT_OF_MEMORY") and (current_mem or rec_mem):
            cons_mem = round_up_gb(max(rec_mem or 0, (current_mem or rec_mem or 0) * 2))
        if ctx.has("TIMEOUT") and (current_time or rec_time):
            cons_time = round_up_minute(max(rec_time or 0, (current_time or rec_time or 0) * 2))
        options.append(
            ResourceOption(
                label="Conservative",
                mem=format_memory_mb(cons_mem) if cons_mem else None,
                time=format_seconds(cons_time) if cons_time else None,
                success_probability="very high",
                queue_impact=_impact(current_mem, cons_mem, current_time, cons_time),
                note="More headroom, but a longer queue wait.",
            )
        )

    return options
