"""Map environment/setup failures found in logs to actionable diagnoses."""

from __future__ import annotations

from slurm_job_doctor.diagnosis.context import DiagnosisContext
from slurm_job_doctor.models.diagnosis import Diagnosis

# log pattern code -> (diagnosis code, severity, title, message)
_ENV_MAP: dict[str, tuple[str, str, str, str]] = {
    "module_not_found": (
        "MODULE_NOT_FOUND",
        "high",
        "Python module not found",
        "A required Python module could not be imported. Make sure the correct "
        "environment or module is loaded before running python.",
    ),
    "import_error": (
        "IMPORT_ERROR",
        "high",
        "Python import failed",
        "An import failed at runtime. Verify the package is installed in the active "
        "environment and that compiled extensions match this node's architecture.",
    ),
    "conda_missing": (
        "CONDA_NOT_FOUND",
        "high",
        "Conda or environment not found",
        "conda or the named environment was not found. Initialize conda (or module load "
        "it) before 'conda activate', and confirm the environment name.",
    ),
    "module_load_error": (
        "MODULE_LOAD_ERROR",
        "high",
        "Environment module failed to load",
        "A 'module load' call failed. Check the module name with 'module avail' and that "
        "it is available on this partition.",
    ),
    "command_not_found": (
        "COMMAND_NOT_FOUND",
        "high",
        "Command not found",
        "A shell command was not on PATH. Load the providing module or fix PATH before "
        "the command runs.",
    ),
    "invalid_partition": (
        "INVALID_PARTITION",
        "high",
        "Invalid partition",
        "The requested partition is invalid or unavailable. List valid partitions with "
        "'sinfo'.",
    ),
    "invalid_account": (
        "INVALID_ACCOUNT",
        "high",
        "Invalid account or QOS",
        "The requested account or QOS is invalid. Check your associations with "
        "'sacctmgr show assoc user=$USER'.",
    ),
}


def diagnose(ctx: DiagnosisContext) -> list[Diagnosis]:
    findings: list[Diagnosis] = []
    for log_code, (code, severity, title, message) in _ENV_MAP.items():
        if not ctx.logs.has(log_code):
            continue
        evidence = [f"log: {line}" for line in ctx.logs.lines_for(log_code)[:2]]
        findings.append(
            Diagnosis(
                code=code,
                category="environment",
                severity=severity,
                title=title,
                message=message,
                evidence=evidence,
            )
        )
    return findings
