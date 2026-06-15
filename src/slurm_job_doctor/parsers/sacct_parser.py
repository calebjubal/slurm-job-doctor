"""Parse ``sacct`` output (``--parsable2`` or CSV) into merged :class:`JobRecord`s."""

from __future__ import annotations

import csv
import re
from collections import OrderedDict
from pathlib import Path

from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.parsers.unit_parser import (
    parse_memory_mb,
    parse_reqmem,
    parse_time_seconds,
)

# Default column order when sacct is run with --noheader (the README's layout).
_DEFAULT_HEADER = [
    "jobid",
    "jobname",
    "state",
    "exitcode",
    "elapsed",
    "timelimit",
    "reqmem",
    "maxrss",
    "alloccpus",
    "ntasks",
    "nodelist",
]

_GPU_TRES_RE = re.compile(r"(?:gres/)?gpu(?::[\w.]+)?=(\d+)", re.IGNORECASE)
_NODELIST_NONE = {"", "NONE", "NONE ASSIGNED", "(NULL)"}


def _to_int(value: str | None) -> int | None:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


# The unit parsers raise on junk by design; in the sacct layer we'd rather degrade to
# None than crash the whole run on one surprising field (e.g. a misaligned column).
def _safe_time(value: str | None) -> int | None:
    try:
        return parse_time_seconds(value)
    except ValueError:
        return None


def _safe_mem(value: str | None) -> int | None:
    try:
        return parse_memory_mb(value)
    except ValueError:
        return None


def _safe_reqmem(value: str | None) -> tuple[int | None, str | None]:
    try:
        return parse_reqmem(value)
    except ValueError:
        return (None, None)


def _split_top_level(text: str) -> list[str]:
    """Split on commas that are not inside ``[...]`` (for compact nodelists)."""
    parts: list[str] = []
    depth = 0
    current = ""
    for char in text:
        if char == "[":
            depth += 1
            current += char
        elif char == "]":
            depth = max(0, depth - 1)
            current += char
        elif char == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += char
    if current:
        parts.append(current)
    return parts


def expand_nodelist(text: str | None) -> list[str]:
    """Expand a Slurm nodelist (``node[001-003],gpu01``) into individual node names."""
    if text is None:
        return []
    text = text.strip()
    if text.upper() in _NODELIST_NONE:
        return []
    nodes: list[str] = []
    for part in _split_top_level(text):
        match = re.match(r"^(.*?)\[([^\]]+)\](.*)$", part)
        if match is None:
            nodes.append(part)
            continue
        prefix, ranges, suffix = match.groups()
        for chunk in ranges.split(","):
            if "-" in chunk:
                start, end = chunk.split("-", 1)
                width = len(start)
                for number in range(int(start), int(end) + 1):
                    nodes.append(f"{prefix}{str(number).zfill(width)}{suffix}")
            else:
                nodes.append(f"{prefix}{chunk}{suffix}")
    return nodes


def _gpu_from_tres(*values: str) -> int | None:
    for value in values:
        if not value:
            continue
        match = _GPU_TRES_RE.search(value)
        if match is not None:
            return int(match.group(1))
    return None


def _merge_group(base_id: str, rows: list[dict[str, str]]) -> JobRecord:
    primary = next((row for row in rows if row.get("jobid", "").strip() == base_id), rows[0])
    ordered = [primary] + [row for row in rows if row is not primary]

    def primary_get(field: str) -> str:
        return (primary.get(field) or "").strip()

    def any_get(field: str) -> str:
        for row in ordered:
            value = (row.get(field) or "").strip()
            if value:
                return value
        return ""

    nodes = expand_nodelist(primary_get("nodelist") or any_get("nodelist"))
    nnodes = _to_int(primary_get("nnodes")) or (len(nodes) or None)
    alloc_cpus = _to_int(primary_get("alloccpus")) or _to_int(any_get("alloccpus"))
    req_cpus = _to_int(primary_get("reqcpus")) or _to_int(any_get("reqcpus"))

    requested_mb, scope = _safe_reqmem(primary_get("reqmem") or any_get("reqmem"))
    if requested_mb is not None:
        if scope == "cpu" and alloc_cpus:
            requested_mb *= alloc_cpus
        elif scope == "node" and nnodes:
            requested_mb *= nnodes

    max_rss: int | None = None
    for row in ordered:
        value = _safe_mem((row.get("maxrss") or "").strip() or None)
        if value is not None:
            max_rss = value if max_rss is None else max(max_rss, value)

    total_cpu: int | None = None
    for row in ordered:
        value = _safe_time((row.get("totalcpu") or "").strip() or None)
        if value is not None:
            total_cpu = value if total_cpu is None else max(total_cpu, value)

    gpu_count = _gpu_from_tres(
        primary_get("alloctres"),
        primary_get("reqtres"),
        any_get("alloctres"),
        any_get("reqtres"),
    )

    return JobRecord(
        job_id=base_id,
        job_name=primary_get("jobname") or None,
        state=primary_get("state"),
        exit_code=primary_get("exitcode") or None,
        elapsed_seconds=_safe_time(primary_get("elapsed") or None),
        timelimit_seconds=_safe_time(primary_get("timelimit") or None),
        requested_memory_mb=requested_mb,
        max_rss_mb=max_rss,
        allocated_cpus=alloc_cpus,
        req_cpus=req_cpus,
        ntasks=_to_int(primary_get("ntasks")) or _to_int(any_get("ntasks")),
        nnodes=nnodes,
        nodes=nodes,
        partition=primary_get("partition") or None,
        account=primary_get("account") or None,
        user=primary_get("user") or None,
        total_cpu_seconds=total_cpu,
        gpu_count=gpu_count,
    )


def parse_sacct_text(text: str) -> list[JobRecord]:
    """Parse sacct output into one merged :class:`JobRecord` per job id."""
    stripped = [line for line in text.splitlines() if line.strip()]
    if not stripped:
        return []

    delimiter = "|" if "|" in stripped[0] else ","
    raw_rows = list(csv.reader(stripped, delimiter=delimiter))

    first = [cell.strip().lower() for cell in raw_rows[0]]
    if "jobid" in first:
        header, data_rows = first, raw_rows[1:]
    else:
        header, data_rows = _DEFAULT_HEADER, raw_rows

    groups: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for cells in data_rows:
        row = {key: (cells[i] if i < len(cells) else "") for i, key in enumerate(header)}
        job_id = row.get("jobid", "").strip()
        if not job_id:
            continue
        base_id = job_id.split(".")[0]
        groups.setdefault(base_id, []).append(row)

    return [_merge_group(base_id, rows) for base_id, rows in groups.items()]


def parse_sacct_file(path: str | Path) -> list[JobRecord]:
    """Read and parse an sacct dump from disk."""
    return parse_sacct_text(Path(path).read_text(encoding="utf-8"))
