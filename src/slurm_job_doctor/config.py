"""Site-tunable configuration: safety factors, diagnosis thresholds, and limits.

Defaults are deliberately conservative (the tool should never pretend to know more than
the cluster). A site can override them with a ``.doctor.yml`` file; see
``docs/`` and the README's "Site-Specific Config" section for the schema.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel


class DoctorConfig(BaseModel):
    # cluster identity
    cluster_name: str | None = None
    default_partition: str | None = None

    # hard limits (None = unknown / unbounded)
    max_mem_gb: float | None = None
    max_walltime_hours: float | None = None

    # policies
    prefer_mem_per_cpu: bool = False
    allow_gpu_recommendations: bool = True

    # safety factors used by the recommenders
    min_memory_safety_factor: float = 1.25
    oom_memory_growth_factor: float = 1.5
    timeout_safety_factor: float = 1.5

    # diagnosis thresholds
    memory_overrequest_ratio: float = 0.4  # MaxRSS below this fraction => over-requested
    memory_near_limit_ratio: float = 0.9  # MaxRSS at/above this fraction => risky
    cpu_efficiency_threshold: float = 0.3  # below this => CPUs over-requested

    @classmethod
    def from_mapping(cls, data: dict) -> DoctorConfig:
        """Build a config from the nested ``.doctor.yml`` structure."""
        cluster = data.get("cluster") or {}
        limits = data.get("limits") or {}
        policies = data.get("policies") or {}
        return cls(
            cluster_name=cluster.get("name"),
            default_partition=cluster.get("default_partition"),
            max_mem_gb=limits.get("max_mem_gb"),
            max_walltime_hours=limits.get("max_walltime_hours"),
            prefer_mem_per_cpu=policies.get("prefer_mem_per_cpu", False),
            allow_gpu_recommendations=policies.get("allow_gpu_recommendations", True),
            min_memory_safety_factor=policies.get("min_memory_safety_factor", 1.25),
            timeout_safety_factor=policies.get("timeout_safety_factor", 1.5),
        )

    @classmethod
    def load(cls, path: str | Path | None) -> DoctorConfig:
        """Load config from a YAML file, or return defaults when ``path`` is falsy."""
        if not path:
            return cls()
        import yaml

        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        return cls.from_mapping(raw)
