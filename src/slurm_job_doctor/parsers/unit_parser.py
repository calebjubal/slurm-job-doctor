"""Normalize Slurm memory and time strings into comparable numeric units.

Memory is normalized to **MiB** (binary, so ``1G == 1024M``) and time to **seconds**.
These helpers are intentionally pure and dependency-free so every other parser and
recommender can rely on a single, well-tested notion of "how big" and "how long".
"""

from __future__ import annotations

import re

__all__ = [
    "parse_memory_mb",
    "parse_reqmem",
    "parse_time_seconds",
    "format_memory_mb",
    "format_seconds",
]

# Values Slurm uses to mean "no value" across the accounting fields we touch.
_MEM_MARKERS = {"", "UNKNOWN", "NONE", "N/A", "NA", "INVALID"}
_TIME_MARKERS = {"", "UNLIMITED", "INVALID", "PARTITION_LIMIT", "UNKNOWN", "NONE", "N/A", "NA"}

# Binary multipliers relative to one MiB.
_MEM_FACTOR: dict[str | None, float] = {
    None: 1.0,
    "k": 1.0 / 1024.0,
    "m": 1.0,
    "g": 1024.0,
    "t": 1024.0 * 1024.0,
    "p": 1024.0 * 1024.0 * 1024.0,
}

# e.g. "16G", "16000M", "15.7G", "16Gn" (per-node), "4Gc" (per-cpu), "512K", "16GB".
_MEM_RE = re.compile(
    r"^(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>[kmgtp])?b?\s*(?P<scope>[nc])?$",
    re.IGNORECASE,
)

_SCOPE = {"n": "node", "c": "cpu"}


def _parse_mem(value: str | int | float | None) -> tuple[int | None, str | None]:
    """Return ``(mib, scope)`` where scope is ``"node"``, ``"cpu"``, or ``None``."""
    if value is None:
        return (None, None)
    text = str(value).strip()
    if text.upper() in _MEM_MARKERS:
        return (None, None)
    match = _MEM_RE.match(text)
    if match is None:
        raise ValueError(f"unrecognized memory value: {value!r}")
    number = float(match.group("num"))
    unit = match.group("unit")
    factor = _MEM_FACTOR[unit.lower() if unit else None]
    mib = int(round(number * factor))
    scope_letter = match.group("scope")
    scope = _SCOPE[scope_letter.lower()] if scope_letter else None
    return (mib, scope)


def parse_memory_mb(value: str | int | float | None) -> int | None:
    """Parse a Slurm memory string to MiB, ignoring any per-node/per-cpu scope.

    >>> parse_memory_mb("16G")
    16384
    >>> parse_memory_mb("16000M")
    16000
    >>> parse_memory_mb("1T")
    1048576
    """
    return _parse_mem(value)[0]


def parse_reqmem(value: str | int | float | None) -> tuple[int | None, str | None]:
    """Parse a Slurm ``ReqMem`` value, keeping its scope.

    ``sacct`` reports requested memory either per node (``16Gn``) or per cpu (``4Gc``).
    The numeric part is returned in MiB and the scope tells the caller whether it still
    needs to be multiplied by node or cpu count to get the total request.

    >>> parse_reqmem("16Gn")
    (16384, 'node')
    >>> parse_reqmem("4Gc")
    (4096, 'cpu')
    """
    return _parse_mem(value)


def parse_time_seconds(value: str | int | None) -> int | None:
    """Parse a Slurm time string to seconds.

    Accepts every documented ``sbatch``/``sacct`` form: bare ``minutes``,
    ``MM:SS``, ``HH:MM:SS``, ``D-HH``, ``D-HH:MM`` and ``D-HH:MM:SS``.

    >>> parse_time_seconds("02:00:00")
    7200
    >>> parse_time_seconds("1-02:00:00")
    93600
    >>> parse_time_seconds("60")
    3600
    """
    if value is None:
        return None
    text = str(value).strip()
    if text.upper() in _TIME_MARKERS:
        return None

    days = 0
    has_day = "-" in text
    if has_day:
        day_str, _, text = text.partition("-")
        days = int(float(day_str))

    parts = text.split(":")
    try:
        nums = [int(float(p)) for p in parts]
    except ValueError as exc:
        raise ValueError(f"unrecognized time value: {value!r}") from exc

    if has_day:
        # The portion after the dash is HH[:MM[:SS]].
        hours = nums[0] if len(nums) > 0 else 0
        minutes = nums[1] if len(nums) > 1 else 0
        seconds = nums[2] if len(nums) > 2 else 0
    elif len(nums) == 1:
        # A lone number is minutes (Slurm's ``--time`` convention).
        hours, minutes, seconds = 0, nums[0], 0
    elif len(nums) == 2:
        hours, minutes, seconds = 0, nums[0], nums[1]
    elif len(nums) == 3:
        hours, minutes, seconds = nums[0], nums[1], nums[2]
    else:
        raise ValueError(f"unrecognized time value: {value!r}")

    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def format_memory_mb(mib: int | float) -> str:
    """Render MiB back into a tidy ``#SBATCH --mem`` value (``24G`` or ``15700M``)."""
    mib = int(round(mib))
    if mib != 0 and mib % 1024 == 0:
        return f"{mib // 1024}G"
    return f"{mib}M"


def format_seconds(seconds: int | float) -> str:
    """Render seconds back into a Slurm ``--time`` value (``HH:MM:SS`` or ``D-HH:MM:SS``)."""
    total = max(0, int(round(seconds)))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)
    if days > 0:
        return f"{days}-{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"
