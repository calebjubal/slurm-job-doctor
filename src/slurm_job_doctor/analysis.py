"""High-level pipeline: evidence in, :class:`Report` out.

This is the seam the CLI and any future API call. It deliberately accepts already-read
text (or a runner callable) so the whole pipeline is testable without a Slurm install.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from slurm_job_doctor.collectors.file_collector import read_optional
from slurm_job_doctor.config import DoctorConfig
from slurm_job_doctor.diagnosis.engine import diagnose
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.models.log_evidence import LogEvidence
from slurm_job_doctor.models.report import Report
from slurm_job_doctor.parsers.log_parser import scan_text
from slurm_job_doctor.parsers.sacct_parser import parse_sacct_text
from slurm_job_doctor.parsers.sbatch_parser import parse_sbatch_file
from slurm_job_doctor.recommenders.engine import recommend


def _select_job(records: list[JobRecord], job_id: str | None) -> JobRecord | None:
    if not records:
        return None
    if job_id:
        for record in records:
            if record.job_id == str(job_id):
                return record
    for record in records:
        if record.is_failed:
            return record
    return records[0]


def analyze(
    *,
    job: JobRecord | None = None,
    script=None,
    logs: LogEvidence | None = None,
    log_text: str | None = None,
    config: DoctorConfig | None = None,
) -> Report:
    """Run diagnosis + recommendation over already-parsed inputs."""
    cfg = config or DoctorConfig()
    evidence = logs if logs is not None else LogEvidence()
    diagnoses = diagnose(job=job, script=script, logs=evidence, config=cfg, log_text=log_text)
    recs = recommend(diagnoses, job=job, script=script, config=cfg)
    return Report(
        job=job,
        script_path=getattr(script, "path", None),
        diagnoses=diagnoses,
        recommendations=recs.items,
        options=recs.options,
    )


def analyze_inputs(
    *,
    job_id: str | None = None,
    sbatch: str | Path | None = None,
    sacct: str | Path | None = None,
    stdout: str | Path | None = None,
    stderr: str | Path | None = None,
    config_path: str | Path | None = None,
    sacct_runner: Callable[[str], str] | None = None,
) -> Report:
    """Gather evidence from files (or a live sacct runner) and analyze it."""
    config = DoctorConfig.load(config_path)
    script = parse_sbatch_file(sbatch) if sbatch else None

    sacct_text = read_optional(sacct)
    if sacct_text is None and job_id and sacct_runner is not None:
        sacct_text = sacct_runner(job_id)

    job = None
    if sacct_text:
        job = _select_job(parse_sacct_text(sacct_text), job_id)

    log_chunks = [text for text in (read_optional(stdout), read_optional(stderr)) if text]
    log_text = "\n".join(log_chunks) if log_chunks else None
    evidence = scan_text(log_text) if log_text else LogEvidence()

    return analyze(job=job, script=script, logs=evidence, log_text=log_text, config=config)
