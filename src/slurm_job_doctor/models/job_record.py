"""Normalized record of a single Slurm job, merged across its accounting rows."""

from __future__ import annotations

from pydantic import BaseModel, Field

# States that mean the job did not finish cleanly.
FAILED_STATES = {
    "FAILED",
    "OUT_OF_MEMORY",
    "TIMEOUT",
    "NODE_FAIL",
    "CANCELLED",
    "BOOT_FAIL",
    "DEADLINE",
    "PREEMPTED",
    "OUT_OF_ME+",  # sacct sometimes truncates the state name
}


class JobRecord(BaseModel):
    """One job's accounting data, normalized to MiB and seconds.

    A single job produces several ``sacct`` rows (the allocation, ``.batch``,
    ``.extern``, and step rows); the parser merges them so that, for example,
    ``ReqMem`` comes from the allocation row while ``MaxRSS`` comes from whichever
    step actually used the most memory.
    """

    job_id: str
    job_name: str | None = None
    state: str = ""
    exit_code: str | None = None
    elapsed_seconds: int | None = None
    timelimit_seconds: int | None = None
    requested_memory_mb: int | None = None
    max_rss_mb: int | None = None
    allocated_cpus: int | None = None
    req_cpus: int | None = None
    ntasks: int | None = None
    nnodes: int | None = None
    nodes: list[str] = Field(default_factory=list)
    partition: str | None = None
    account: str | None = None
    user: str | None = None
    total_cpu_seconds: int | None = None
    gpu_count: int | None = None

    @property
    def state_base(self) -> str:
        """State without trailing detail, e.g. ``CANCELLED by 1001`` → ``CANCELLED``."""
        return self.state.split()[0].upper() if self.state.strip() else ""

    @property
    def is_oom(self) -> bool:
        return self.state_base == "OUT_OF_MEMORY"

    @property
    def is_timeout(self) -> bool:
        return self.state_base == "TIMEOUT"

    @property
    def is_failed(self) -> bool:
        return self.state_base in FAILED_STATES

    @property
    def cpu_efficiency(self) -> float | None:
        """TotalCPU / (Elapsed × AllocCPUS); ``None`` when inputs are missing."""
        if self.total_cpu_seconds is None or not self.elapsed_seconds or not self.allocated_cpus:
            return None
        denominator = self.elapsed_seconds * self.allocated_cpus
        if denominator <= 0:
            return None
        return self.total_cpu_seconds / denominator

    @property
    def memory_utilization(self) -> float | None:
        """MaxRSS / ReqMem; ``None`` when either is missing."""
        if self.max_rss_mb is None or not self.requested_memory_mb:
            return None
        return self.max_rss_mb / self.requested_memory_mb
