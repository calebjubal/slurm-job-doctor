"""Detect host (cgroup) and GPU (CUDA) out-of-memory failures."""

from __future__ import annotations

from slurm_job_doctor.diagnosis.context import DiagnosisContext
from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.parsers.unit_parser import format_memory_mb


def diagnose(ctx: DiagnosisContext) -> list[Diagnosis]:
    job = ctx.job
    logs = ctx.logs
    findings: list[Diagnosis] = []

    if logs.has("cuda_oom"):
        evidence = [f"stderr: {line}" for line in logs.lines_for("cuda_oom")[:2]]
        gpus = (job.gpu_count if job else None) or None
        if gpus:
            evidence.append(f"GPUs requested: {gpus}")
        findings.append(
            Diagnosis(
                code="CUDA_OUT_OF_MEMORY",
                category="gpu",
                severity="critical",
                title="GPU ran out of memory",
                message=(
                    "The job exceeded the memory available on the GPU. Reduce the batch "
                    "size, use gradient accumulation or activation checkpointing, or "
                    "request a larger-memory GPU."
                ),
                evidence=evidence,
            )
        )

    host_oom = (job is not None and job.is_oom) or logs.has("oom_kill")
    if host_oom:
        evidence = []
        if job is not None:
            if job.state:
                evidence.append(f"State: {job.state}")
            if job.requested_memory_mb:
                evidence.append(f"Requested memory: {format_memory_mb(job.requested_memory_mb)}")
            if job.max_rss_mb:
                evidence.append(f"Max RSS: {format_memory_mb(job.max_rss_mb)}")
            if job.memory_utilization is not None:
                evidence.append(f"Memory utilization: {job.memory_utilization * 100:.0f}%")
        evidence.extend(f"log: {line}" for line in logs.lines_for("oom_kill")[:2])
        findings.append(
            Diagnosis(
                code="OUT_OF_MEMORY",
                category="memory",
                severity="critical",
                title="Job killed: out of memory",
                message=(
                    "The job was killed because it used more memory than it requested. "
                    "Request more memory before resubmitting."
                ),
                evidence=evidence,
            )
        )

    return findings
