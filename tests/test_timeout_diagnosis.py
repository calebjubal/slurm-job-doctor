from slurm_job_doctor.diagnosis.engine import diagnose, primary
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.parsers.log_parser import scan_text


def test_timeout_state_is_critical():
    job = JobRecord(
        job_id="1002",
        state="TIMEOUT",
        elapsed_seconds=7200,
        timelimit_seconds=7200,
    )
    findings = diagnose(job=job)
    top = primary(findings)
    assert top.code == "TIMEOUT"
    assert top.severity == "critical"
    assert any("Elapsed" in line for line in top.evidence)
    assert any("Time limit" in line for line in top.evidence)


def test_timeout_detected_from_logs():
    logs = scan_text("*** JOB 1 CANCELLED AT 2025-01-01 DUE TO TIME LIMIT ***\n")
    findings = diagnose(logs=logs)
    assert primary(findings).code == "TIMEOUT"
