"""Thin, mockable wrapper around running an external command."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run(cmd: list[str], timeout: float = 30.0) -> CommandResult:
    """Run ``cmd`` and capture its output, never raising on a non-zero exit."""
    try:
        completed = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return CommandResult(127, "", f"{cmd[0]}: command not found ({exc})")
    except subprocess.TimeoutExpired:
        return CommandResult(124, "", f"{cmd[0]}: timed out after {timeout}s")
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)
