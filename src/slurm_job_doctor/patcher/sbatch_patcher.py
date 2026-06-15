"""Apply directive recommendations to an sbatch script, preserving everything else."""

from __future__ import annotations

import difflib
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.models.recommendation import Recommendation
from slurm_job_doctor.models.sbatch_script import SbatchScript
from slurm_job_doctor.parsers.sbatch_parser import parse_sbatch_file, parse_sbatch_text
from slurm_job_doctor.patcher.safety import filter_recommendations

_OMP_RE = re.compile(r"OMP_NUM_THREADS\s*=")


@dataclass
class PatchResult:
    patched_text: str
    changed: list[str] = field(default_factory=list)  # directive keys changed/added
    diff: str = ""
    output_path: str | None = None
    backup_path: str | None = None
    applied: bool = False


def _leading_whitespace(line: str) -> str:
    return line[: len(line) - len(line.lstrip())]


def _replace_value(raw: str, old: str | None, new: str) -> str | None:
    """Swap a directive's value in place, keeping the original line style and comments."""
    if old and old in raw:
        index = raw.rfind(old)
        return raw[:index] + new + raw[index + len(old) :]
    return None


def _canonical_directive(raw: str, key: str, new: str) -> str:
    return f"{_leading_whitespace(raw)}#SBATCH --{key}={new}"


def _first_body_index(lines: list[str]) -> int:
    """Index of the first executable command line (after shebang/#SBATCH/comments)."""
    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return index
    return len(lines)


def _apply_omp(lines: list[str], recommendations: list[Recommendation]) -> bool:
    omp = next(
        (r for r in recommendations if r.kind == "script" and r.directive == "OMP_NUM_THREADS"),
        None,
    )
    if omp is None:
        return False
    target = f"export OMP_NUM_THREADS={omp.new_value}"
    for index, line in enumerate(lines):
        if _OMP_RE.search(line) and not line.strip().startswith("#"):
            lines[index] = _leading_whitespace(line) + target
            return True
    insert_at = _first_body_index(lines)
    lines[insert_at:insert_at] = [target]
    return True


def patch_text(
    script: SbatchScript,
    recommendations: list[Recommendation],
    diagnoses: list[Diagnosis] | None = None,
) -> PatchResult:
    """Return the patched script text plus the list of directives that changed."""
    safe = filter_recommendations(recommendations, diagnoses or [])
    directive_recs = {
        rec.key: rec for rec in safe if rec.kind == "directive" and rec.new_value is not None
    }

    original = list(script.lines)
    lines = list(script.lines)
    changed: list[str] = []

    # Replace existing directives (last occurrence wins, mirroring Slurm).
    last_directive_for_key = {d.key: d for d in script.directives}
    handled: set[str] = set()
    for key, rec in directive_recs.items():
        directive = last_directive_for_key.get(key)
        if directive is None:
            continue
        new_line = _replace_value(directive.raw, directive.value, rec.new_value) or (
            _canonical_directive(directive.raw, key, rec.new_value)
        )
        lines[directive.line_index] = new_line
        handled.add(key)
        changed.append(key)

    # Insert directives that did not exist yet, after the last #SBATCH line.
    missing = [(key, rec) for key, rec in directive_recs.items() if key not in handled]
    if missing:
        last_sbatch = max(
            (d.line_index for d in script.directives),
            default=0 if script.shebang else -1,
        )
        insert_at = last_sbatch + 1
        new_lines = [f"#SBATCH --{key}={rec.new_value}" for key, rec in missing]
        lines[insert_at:insert_at] = new_lines
        changed.extend(key for key, _ in missing)

    if _apply_omp(lines, safe):
        changed.append("OMP_NUM_THREADS")

    patched_text = "\n".join(lines) + "\n"
    diff = "".join(
        difflib.unified_diff(
            [line + "\n" for line in original],
            [line + "\n" for line in lines],
            fromfile=script.path or "original.sbatch",
            tofile=(script.path or "original.sbatch") + " (patched)",
        )
    )
    return PatchResult(patched_text=patched_text, changed=changed, diff=diff)


def _doctor_path(path: Path) -> Path:
    return path.with_name(path.stem + ".doctor" + (path.suffix or ".sbatch"))


def patch_file(
    path: str | Path,
    recommendations: list[Recommendation],
    diagnoses: list[Diagnosis] | None = None,
    *,
    output: str | Path | None = None,
    apply: bool = False,
) -> PatchResult:
    """Patch a script on disk.

    Without ``apply`` the patched script is written to ``<name>.doctor.sbatch`` (or
    ``output``). With ``apply`` the original is backed up to ``<name>.bak`` first and
    then overwritten in place.
    """
    source = Path(path)
    script = parse_sbatch_file(source)
    result = patch_text(script, recommendations, diagnoses)

    if apply:
        backup = source.with_name(source.name + ".bak")
        shutil.copy2(source, backup)
        source.write_text(result.patched_text, encoding="utf-8")
        result.backup_path = str(backup)
        result.output_path = str(source)
        result.applied = True
    else:
        destination = Path(output) if output else _doctor_path(source)
        destination.write_text(result.patched_text, encoding="utf-8")
        result.output_path = str(destination)

    return result


# Re-exported for convenience in tests and callers that already hold script text.
def patch_script_text(
    text: str,
    recommendations: list[Recommendation],
    diagnoses: list[Diagnosis] | None = None,
    path: str | None = None,
) -> PatchResult:
    return patch_text(parse_sbatch_text(text, path=path), recommendations, diagnoses)
