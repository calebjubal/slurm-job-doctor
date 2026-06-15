"""Read local evidence files."""

from __future__ import annotations

from pathlib import Path


def read_optional(path: str | Path | None) -> str | None:
    """Read a file if the path is set and exists, else return None."""
    if not path:
        return None
    file_path = Path(path)
    if not file_path.exists():
        return None
    return file_path.read_text(encoding="utf-8", errors="replace")
