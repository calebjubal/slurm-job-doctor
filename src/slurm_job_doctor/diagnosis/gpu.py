"""Flag GPUs that were requested but show no sign of being used."""

from __future__ import annotations

import re

from slurm_job_doctor.diagnosis.context import DiagnosisContext
from slurm_job_doctor.models.diagnosis import Diagnosis

_GPU_ACTIVITY_RE = re.compile(
    r"cuda|gpu|nvidia|cudnn|nccl|device:\s*cuda|tensor core", re.IGNORECASE
)


def diagnose(ctx: DiagnosisContext) -> list[Diagnosis]:
    job = ctx.job
    script = ctx.script

    requested = 0
    if script is not None and script.gpu_count:
        requested = script.gpu_count
    if job is not None and job.gpu_count:
        requested = max(requested, job.gpu_count)
    if requested <= 0:
        return []

    # A CUDA OOM proves the GPU was used.
    if ctx.logs.has("cuda_oom"):
        return []

    # Only reason about GPU usage when we actually have logs to inspect; otherwise we
    # cannot tell "unused" from "we just weren't given the logs".
    if not ctx.has_logs:
        return []
    if ctx.log_text and _GPU_ACTIVITY_RE.search(ctx.log_text):
        return []

    return [
        Diagnosis(
            code="GPU_POSSIBLY_UNUSED",
            category="gpu",
            severity="medium",
            title="GPU requested but possibly unused",
            message=(
                f"The job requested {requested} GPU(s), but the logs show no CUDA/GPU "
                "activity. If this is a CPU-only job, drop the GPU request to cut queue "
                "time; otherwise add a GPU sanity check (e.g. nvidia-smi or "
                "torch.cuda.is_available())."
            ),
            evidence=[
                f"GPUs requested: {requested}",
                "No CUDA/GPU activity found in the provided logs",
            ],
        )
    ]
