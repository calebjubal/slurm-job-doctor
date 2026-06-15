"""Guardrails that drop unsafe edits before the patcher touches a script.

The tool must never make a job *more* likely to fail. The most important rule: after an
out-of-memory failure, never emit a smaller memory request.
"""

from __future__ import annotations

from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.models.recommendation import Recommendation
from slurm_job_doctor.parsers.unit_parser import parse_memory_mb, parse_time_seconds


def _has(diagnoses: list[Diagnosis], code: str) -> bool:
    return any(diagnosis.code == code for diagnosis in diagnoses)


def is_safe(rec: Recommendation, diagnoses: list[Diagnosis]) -> bool:
    """Return False for an edit that would reduce a resource a failure needed more of."""
    if rec.kind != "directive" or rec.new_value is None:
        return True

    if rec.directive == "--mem" and _has(diagnoses, "OUT_OF_MEMORY"):
        old = parse_memory_mb(rec.old_value) if rec.old_value else None
        new = parse_memory_mb(rec.new_value)
        if old is not None and new is not None and new < old:
            return False

    if rec.directive == "--time" and _has(diagnoses, "TIMEOUT"):
        old = parse_time_seconds(rec.old_value) if rec.old_value else None
        new = parse_time_seconds(rec.new_value)
        if old is not None and new is not None and new < old:
            return False

    return True


def filter_recommendations(
    recommendations: list[Recommendation], diagnoses: list[Diagnosis]
) -> list[Recommendation]:
    """Drop any recommendation that violates a safety rule."""
    return [rec for rec in recommendations if is_safe(rec, diagnoses)]
