"""Helpers shared by the resource recommenders."""

from __future__ import annotations

import math

from slurm_job_doctor.config import DoctorConfig
from slurm_job_doctor.parsers.unit_parser import format_memory_mb
from slurm_job_doctor.recommenders.context import RecommendationContext


def to_int(value: str | None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def current_memory_mb(ctx: RecommendationContext) -> tuple[int | None, str | None]:
    """Current requested memory as (MiB, display string), preferring the script."""
    if ctx.script is not None and ctx.script.mem:
        from slurm_job_doctor.parsers.unit_parser import parse_memory_mb

        return parse_memory_mb(ctx.script.mem), ctx.script.mem
    if ctx.job is not None and ctx.job.requested_memory_mb:
        return ctx.job.requested_memory_mb, format_memory_mb(ctx.job.requested_memory_mb)
    return None, None


def current_time_seconds(ctx: RecommendationContext) -> tuple[int | None, str | None]:
    """Current walltime as (seconds, display string), preferring the script."""
    if ctx.script is not None and ctx.script.time:
        from slurm_job_doctor.parsers.unit_parser import parse_time_seconds

        return parse_time_seconds(ctx.script.time), ctx.script.time
    if ctx.job is not None and ctx.job.timelimit_seconds:
        from slurm_job_doctor.parsers.unit_parser import format_seconds

        return ctx.job.timelimit_seconds, format_seconds(ctx.job.timelimit_seconds)
    return None, None


def round_up_gb(mb: float) -> int:
    """Round MiB up to a whole GiB (recommendations should be tidy values)."""
    return int(math.ceil(mb / 1024.0)) * 1024


def round_up_minute(seconds: float) -> int:
    return int(math.ceil(seconds / 60.0)) * 60


def cap_memory(mb: int, config: DoctorConfig) -> int:
    if config.max_mem_gb:
        return min(mb, int(config.max_mem_gb * 1024))
    return mb


def cap_time(seconds: int, config: DoctorConfig) -> int:
    if config.max_walltime_hours:
        return min(seconds, int(config.max_walltime_hours * 3600))
    return seconds
