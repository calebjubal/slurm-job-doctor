"""Catch-all diagnoses for failed states not covered by a more specific rule."""

from __future__ import annotations

from slurm_job_doctor.diagnosis.context import DiagnosisContext
from slurm_job_doctor.models.diagnosis import Diagnosis

# state -> (diagnosis code, severity, title, message)
_STATE_MAP: dict[str, tuple[str, str, str, str]] = {
    "NODE_FAIL": (
        "NODE_FAILURE",
        "high",
        "Node failure",
        "A compute node failed during the job. This is usually a cluster problem rather "
        "than your script — resubmit, and report it to support if it recurs.",
    ),
    "BOOT_FAIL": (
        "BOOT_FAIL",
        "high",
        "Node boot failure",
        "A node failed to boot for this job. Resubmit; report it if it keeps happening.",
    ),
    "DEADLINE": (
        "DEADLINE",
        "high",
        "Scheduling deadline reached",
        "The job reached its scheduling deadline before completing. Adjust --deadline or "
        "--time, or submit earlier.",
    ),
    "PREEMPTED": (
        "PREEMPTED",
        "medium",
        "Job preempted",
        "A higher-priority job preempted this one. Use checkpointing with --requeue so the "
        "work can resume automatically.",
    ),
    "CANCELLED": (
        "JOB_CANCELLED",
        "medium",
        "Job cancelled",
        "The job was cancelled by a user, admin, or the scheduler. If this was "
        "unexpected, check for preemption or an accidental scancel.",
    ),
    "FAILED": (
        "JOB_FAILED",
        "high",
        "Job failed",
        "The job exited with a non-zero status. Inspect stderr for the root cause; the "
        "exit code's second number is the terminating signal, if any.",
    ),
}


def diagnose(ctx: DiagnosisContext) -> list[Diagnosis]:
    job = ctx.job
    if job is None or not job.is_failed:
        return []

    state = job.state_base
    # OOM and TIMEOUT are handled by their dedicated rules.
    if state in {"OUT_OF_MEMORY", "TIMEOUT"} or state not in _STATE_MAP:
        return []

    code, severity, title, message = _STATE_MAP[state]
    evidence = [f"State: {job.state}"]
    if job.exit_code:
        evidence.append(f"Exit code: {job.exit_code}")
    return [
        Diagnosis(
            code=code,
            category="state",
            severity=severity,
            title=title,
            message=message,
            evidence=evidence,
        )
    ]
