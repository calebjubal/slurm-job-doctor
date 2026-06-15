"""Parse ``#SBATCH`` directives out of a batch script while preserving its layout."""

from __future__ import annotations

import re
import shlex
from pathlib import Path

from slurm_job_doctor.models.sbatch_script import SbatchDirective, SbatchScript

_SBATCH_RE = re.compile(r"^\s*#SBATCH\s+(.*)$")

# Short option to long-option mapping for the directives we care about.
_SHORT_TO_LONG = {
    "J": "job-name",
    "p": "partition",
    "A": "account",
    "N": "nodes",
    "n": "ntasks",
    "c": "cpus-per-task",
    "t": "time",
    "o": "output",
    "e": "error",
    "G": "gpus",
    "a": "array",
    "d": "dependency",
    "w": "nodelist",
    "C": "constraint",
    "D": "chdir",
}


def _parse_directive_tokens(remainder: str) -> list[tuple[str, str | None]]:
    """Split the text after ``#SBATCH`` into (key, value) pairs."""
    try:
        tokens = shlex.split(remainder, comments=True)
    except ValueError:
        tokens = remainder.split()

    pairs: list[tuple[str, str | None]] = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        value: str | None
        if token.startswith("--"):
            body = token[2:]
            if "=" in body:
                key, value = body.split("=", 1)
            else:
                key, value = body, None
                if index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
                    value = tokens[index + 1]
                    index += 1
            pairs.append((key.lower(), value))
        elif token.startswith("-") and len(token) > 1:
            letter = token[1]
            key = _SHORT_TO_LONG.get(letter, letter)
            attached = token[2:]
            if attached.startswith("="):
                value = attached[1:]
            elif attached:
                value = attached
            else:
                value = None
                if index + 1 < len(tokens) and not tokens[index + 1].startswith("-"):
                    value = tokens[index + 1]
                    index += 1
            pairs.append((key.lower(), value))
        index += 1
    return pairs


def parse_sbatch_text(text: str, path: str | None = None) -> SbatchScript:
    """Parse the contents of a batch script into an :class:`SbatchScript`."""
    lines = text.splitlines()
    shebang = lines[0] if lines and lines[0].startswith("#!") else None

    directives: list[SbatchDirective] = []
    for line_index, line in enumerate(lines):
        match = _SBATCH_RE.match(line)
        if match is None:
            continue
        for key, value in _parse_directive_tokens(match.group(1).strip()):
            directives.append(
                SbatchDirective(key=key, value=value, raw=line, line_index=line_index)
            )

    return SbatchScript(path=path, lines=lines, directives=directives, shebang=shebang)


def parse_sbatch_file(path: str | Path) -> SbatchScript:
    """Read and parse a batch script from disk."""
    text = Path(path).read_text(encoding="utf-8")
    return parse_sbatch_text(text, path=str(path))
