"""Scan job stdout/stderr for known failure signatures."""

from __future__ import annotations

from pathlib import Path

from slurm_job_doctor.diagnosis.patterns import PATTERNS
from slurm_job_doctor.models.log_evidence import LogEvidence, LogMatch

# Cap matches per pattern so a log that repeats an error thousands of times
# does not flood the evidence with identical lines.
_MAX_PER_CODE = 5
_MAX_LINE_LENGTH = 300


def scan_text(text: str, source: str | None = None) -> LogEvidence:
    """Scan log text and return the failure patterns it contains."""
    matches: list[LogMatch] = []
    counts: dict[str, int] = {}

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        for pattern in PATTERNS:
            if pattern.regex.search(line) is None:
                continue
            if counts.get(pattern.code, 0) >= _MAX_PER_CODE:
                break
            counts[pattern.code] = counts.get(pattern.code, 0) + 1
            matches.append(
                LogMatch(
                    code=pattern.code,
                    category=pattern.category,
                    severity=pattern.severity,
                    line_number=line_number,
                    line=line[:_MAX_LINE_LENGTH],
                    source=source,
                )
            )
            break  # first matching pattern wins for this line
    return LogEvidence(matches=matches)


def scan_file(path: str | Path) -> LogEvidence:
    """Scan a single log file (missing files yield empty evidence)."""
    file_path = Path(path)
    if not file_path.exists():
        return LogEvidence()
    text = file_path.read_text(encoding="utf-8", errors="replace")
    return scan_text(text, source=file_path.name)


def scan_files(paths: list[str | Path | None]) -> LogEvidence:
    """Scan several log files and merge their evidence."""
    evidence = LogEvidence()
    for path in paths:
        if path is None:
            continue
        evidence = evidence.merge(scan_file(path))
    return evidence
