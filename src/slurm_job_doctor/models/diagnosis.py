"""A single finding produced by the diagnosis engine."""

from __future__ import annotations

from pydantic import BaseModel, Field

SEVERITY_RANK = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


class Diagnosis(BaseModel):
    code: str  # machine code, e.g. "OUT_OF_MEMORY"
    category: str  # memory / timeout / cpu / gpu / environment / state
    severity: str  # info / low / medium / high / critical
    title: str  # short human-readable headline
    message: str  # explanation and what to do about it
    evidence: list[str] = Field(default_factory=list)

    @property
    def rank(self) -> int:
        return SEVERITY_RANK.get(self.severity, 0)
