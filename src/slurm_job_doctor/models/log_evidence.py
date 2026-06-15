"""Structured evidence extracted from a job's stdout/stderr logs."""

from __future__ import annotations

from pydantic import BaseModel, Field

# Ordering used to pick the single most serious signal in a log.
SEVERITY_ORDER = {"none": -1, "low": 0, "medium": 1, "high": 2, "critical": 3}


def max_severity(severities: list[str]) -> str:
    """Return the most serious severity in ``severities`` (``"none"`` if empty)."""
    best = "none"
    for severity in severities:
        if SEVERITY_ORDER.get(severity, 0) > SEVERITY_ORDER.get(best, -1):
            best = severity
    return best


class LogMatch(BaseModel):
    """A single line that matched a known failure pattern."""

    code: str
    category: str
    severity: str
    line_number: int
    line: str
    source: str | None = None


class LogEvidence(BaseModel):
    """All pattern matches found across one or more log files."""

    matches: list[LogMatch] = Field(default_factory=list)

    @property
    def matched_patterns(self) -> list[str]:
        """Unique pattern codes, in first-seen order."""
        seen: list[str] = []
        for match in self.matches:
            if match.code not in seen:
                seen.append(match.code)
        return seen

    @property
    def categories(self) -> list[str]:
        seen: list[str] = []
        for match in self.matches:
            if match.category not in seen:
                seen.append(match.category)
        return seen

    @property
    def important_lines(self) -> list[str]:
        seen: list[str] = []
        for match in self.matches:
            if match.line not in seen:
                seen.append(match.line)
        return seen

    @property
    def severity(self) -> str:
        if not self.matches:
            return "none"
        return max_severity([match.severity for match in self.matches])

    def has(self, code: str) -> bool:
        return any(match.code == code for match in self.matches)

    def has_category(self, category: str) -> bool:
        return any(match.category == category for match in self.matches)

    def lines_for(self, code: str) -> list[str]:
        return [match.line for match in self.matches if match.code == code]

    def merge(self, other: LogEvidence) -> LogEvidence:
        return LogEvidence(matches=[*self.matches, *other.matches])
