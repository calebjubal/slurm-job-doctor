from slurm_job_doctor.diagnosis.engine import diagnose, primary
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.parsers.log_parser import scan_text


def oom_job() -> JobRecord:
    return JobRecord(
        job_id="123456",
        job_name="train",
        state="OUT_OF_MEMORY",
        exit_code="0:125",
        requested_memory_mb=16384,
        max_rss_mb=15700,
        allocated_cpus=8,
        elapsed_seconds=751,
    )


def test_oom_state_produces_critical_primary():
    findings = diagnose(job=oom_job())
    top = primary(findings)
    assert top is not None
    assert top.code == "OUT_OF_MEMORY"
    assert top.severity == "critical"
    # evidence cites the requested vs observed memory
    assert any("Requested memory" in line for line in top.evidence)
    assert any("Max RSS" in line for line in top.evidence)


def test_oom_does_not_also_recommend_lowering_memory():
    findings = diagnose(job=oom_job())
    codes = {d.code for d in findings}
    assert "MEMORY_OVER_REQUESTED" not in codes
    assert "MEMORY_NEAR_LIMIT" not in codes


def test_oom_detected_from_logs_without_sacct():
    logs = scan_text("slurmstepd: Detected 1 oom-kill event(s) in StepId=1.batch\n")
    findings = diagnose(logs=logs)
    assert primary(findings).code == "OUT_OF_MEMORY"


def test_cuda_oom_is_a_gpu_diagnosis():
    logs = scan_text("RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB\n")
    job = JobRecord(job_id="9", state="FAILED", gpu_count=1)
    findings = diagnose(job=job, logs=logs)
    codes = {d.code for d in findings}
    assert "CUDA_OUT_OF_MEMORY" in codes
    cuda = next(d for d in findings if d.code == "CUDA_OUT_OF_MEMORY")
    assert cuda.category == "gpu"
    assert cuda.severity == "critical"
