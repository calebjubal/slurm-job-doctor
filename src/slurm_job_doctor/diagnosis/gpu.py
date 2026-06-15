"""Flag GPUs that were requested but show no sign of being used."""

from __future__ import annotations

import re

from slurm_job_doctor.diagnosis.context import DiagnosisContext
from slurm_job_doctor.models.diagnosis import Diagnosis

# Positive evidence that the GPU was actually used. Kept specific so that a line like
# "no CUDA device selected, running on CPU" does NOT count as usage.
_GPU_USED_RE = re.compile(
    r"using device:\s*cuda"
    r"|device\s*=\s*cuda"
    r"|cuda:\d"
    r"|to\(['\"]cuda"
    r"|\.cuda\(\)"
    r"|moved to (?:cuda|gpu)"
    r"|nvidia-smi"
    r"|CUDA available"
    r"|torch\.cuda\.is_available\(\)\s*[:=]?\s*true"
    r"|allocated[^\n]*on gpu",
    re.IGNORECASE,
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

    # Only reason about usage when we actually have logs; otherwise we cannot tell
    # "unused" from "we just weren't given the logs".
    if not ctx.has_logs:
        return []

    # If the logs show concrete GPU usage, the request was justified.
    if ctx.log_text and _GPU_USED_RE.search(ctx.log_text):
        return []

    return [
        Diagnosis(
            code="GPU_POSSIBLY_UNUSED",
            category="gpu",
            severity="medium",
            title="GPU requested but possibly unused",
            message=(
                f"The job requested {requested} GPU(s), but the logs show no sign of GPU "
                "use. If this is a CPU-only job, drop the GPU request to cut queue time; "
                "otherwise add a GPU sanity check (e.g. torch.cuda.is_available())."
            ),
            evidence=[
                f"GPUs requested: {requested}",
                "No GPU usage found in the provided logs",
            ],
        )
    ]
