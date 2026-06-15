"""Collect completed-job accounting via ``sacct``."""

from __future__ import annotations

from collections.abc import Callable

from slurm_job_doctor.collectors.command_runner import CommandResult, run

# Fields we ask sacct for. A header is emitted (no --noheader) so the parser can map
# columns by name regardless of order.
SACCT_FORMAT = ",".join(
    [
        "JobID",
        "JobName",
        "State",
        "ExitCode",
        "Elapsed",
        "Timelimit",
        "ReqMem",
        "MaxRSS",
        "AllocCPUS",
        "ReqCPUS",
        "NTasks",
        "NNodes",
        "NodeList",
        "Partition",
        "Account",
        "User",
        "TotalCPU",
        "AllocTRES",
    ]
)

Runner = Callable[[list[str]], CommandResult]


def build_command(job_id: str) -> list[str]:
    return ["sacct", "--jobs", str(job_id), f"--format={SACCT_FORMAT}", "--parsable2"]


def collect(job_id: str, runner: Runner = run) -> str:
    """Return raw sacct output for ``job_id`` (raises if sacct is unavailable/fails)."""
    result = runner(build_command(job_id))
    if not result.ok:
        detail = result.stderr.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"sacct failed for job {job_id}: {detail}")
    return result.stdout
