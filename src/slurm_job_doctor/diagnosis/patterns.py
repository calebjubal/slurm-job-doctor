"""Regex patterns for known Slurm/HPC failure signatures found in job logs.

Patterns are tried top-to-bottom and the first match on a line wins, so the more
specific signatures (e.g. CUDA OOM) are listed before the more general ones (host OOM).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class LogPattern:
    code: str
    category: str
    severity: str
    regex: re.Pattern[str]
    summary: str


def _pattern(code: str, category: str, severity: str, source: str, summary: str) -> LogPattern:
    return LogPattern(code, category, severity, re.compile(source, re.IGNORECASE), summary)


PATTERNS: list[LogPattern] = [
    _pattern(
        "cuda_oom",
        "gpu",
        "critical",
        r"CUDA out of memory|CUDA_ERROR_OUT_OF_MEMORY|torch\.cuda\.OutOfMemoryError|"
        r"cuda(?:Malloc)?.{0,40}out of memory",
        "CUDA ran out of GPU memory.",
    ),
    _pattern(
        "oom_kill",
        "memory",
        "critical",
        r"oom[-_ ]?kill|out of memory|killed process \d+|memory cgroup out of memory|"
        r"oom[-_]?reaper|received signal 9|signal 9 \(killed\)",
        "A process was killed by the out-of-memory handler.",
    ),
    _pattern(
        "cannot_allocate_memory",
        "memory",
        "high",
        r"cannot allocate memory|std::bad_alloc|\bbad_alloc\b|\bMemoryError\b",
        "A memory allocation failed.",
    ),
    _pattern(
        "timeout",
        "timeout",
        "critical",
        r"DUE TO TIME LIMIT|TIME LIMIT EXCEEDED|CANCELLED AT .* DUE TO TIME LIMIT",
        "The job hit its walltime limit.",
    ),
    _pattern(
        "module_not_found",
        "environment",
        "high",
        r"ModuleNotFoundError|No module named",
        "A Python module could not be imported.",
    ),
    _pattern(
        "conda_missing",
        "environment",
        "high",
        r"conda: command not found|No command 'conda'|Could not find conda environment|"
        r"\bCondaError\b|EnvironmentNameNotFound|EnvironmentLocationNotFound",
        "Conda or a named conda environment was not found.",
    ),
    _pattern(
        "module_load_error",
        "environment",
        "high",
        r"Lmod has detected the following error|module: command not found|"
        r"Unable to locate a modulefile",
        "An environment module failed to load.",
    ),
    _pattern(
        "import_error",
        "environment",
        "high",
        r"\bImportError\b",
        "A Python import failed.",
    ),
    _pattern(
        "command_not_found",
        "environment",
        "high",
        r"command not found|: not found$",
        "A shell command was not found on PATH.",
    ),
    _pattern(
        "invalid_partition",
        "environment",
        "high",
        r"invalid partition|partition .* not found|requested partition.*not (?:exist|available)",
        "The requested partition is invalid or unavailable.",
    ),
    _pattern(
        "invalid_account",
        "environment",
        "high",
        r"invalid account|invalid account or account/partition|invalid qos",
        "The requested account or QOS is invalid.",
    ),
    _pattern(
        "disk_quota",
        "io",
        "high",
        r"Disk quota exceeded|No space left on device",
        "The job ran out of disk space or quota.",
    ),
    _pattern(
        "no_such_file",
        "io",
        "medium",
        r"No such file or directory",
        "A referenced file or directory does not exist.",
    ),
    _pattern(
        "permission_denied",
        "io",
        "medium",
        r"Permission denied",
        "A file operation was denied by permissions.",
    ),
    _pattern(
        "segfault",
        "runtime",
        "high",
        r"Segmentation fault|signal 11|core dumped",
        "The process crashed with a segmentation fault.",
    ),
]

PATTERNS_BY_CODE: dict[str, LogPattern] = {pattern.code: pattern for pattern in PATTERNS}
