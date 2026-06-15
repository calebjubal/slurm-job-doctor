"""Recommend dropping a GPU request when nothing used it."""

from __future__ import annotations

from slurm_job_doctor.models.recommendation import Recommendation
from slurm_job_doctor.recommenders.context import RecommendationContext


def recommend(ctx: RecommendationContext) -> list[Recommendation]:
    if not (ctx.has("GPU_POSSIBLY_UNUSED") and ctx.config.allow_gpu_recommendations):
        return []
    current = ctx.script.gres if ctx.script else None
    return [
        Recommendation(
            directive="--gres",
            old_value=current,
            new_value=None,  # suggest removal
            reason=(
                "No GPU activity in the logs; if this job is CPU-only, drop the GPU "
                "request to cut queue time. Keep it if the GPU work just wasn't logged."
            ),
            kind="note",
        )
    ]
