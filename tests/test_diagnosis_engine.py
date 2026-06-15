from slurm_job_doctor.diagnosis.engine import diagnose
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.parsers.log_parser import scan_text
from slurm_job_doctor.parsers.sbatch_parser import parse_sbatch_text


def codes(findings):
    return {d.code for d in findings}


def test_memory_over_requested():
    job = JobRecord(
        job_id="1",
        state="COMPLETED",
        requested_memory_mb=32768,
        max_rss_mb=4096,  # 12.5% utilization
        allocated_cpus=1,
    )
    assert "MEMORY_OVER_REQUESTED" in codes(diagnose(job=job))


def test_memory_near_limit_warns_even_when_completed():
    job = JobRecord(
        job_id="1",
        state="COMPLETED",
        requested_memory_mb=16384,
        max_rss_mb=15800,  # ~96%
    )
    assert "MEMORY_NEAR_LIMIT" in codes(diagnose(job=job))


def test_low_cpu_efficiency():
    job = JobRecord(
        job_id="2",
        state="COMPLETED",
        allocated_cpus=16,
        elapsed_seconds=3600,
        total_cpu_seconds=3600,  # 1 core-hour of 16 => ~6% efficiency
    )
    assert "CPU_OVER_REQUESTED" in codes(diagnose(job=job))


def test_openmp_mismatch_from_script():
    script = parse_sbatch_text(
        "#!/bin/bash\n#SBATCH --cpus-per-task=32\nexport OMP_NUM_THREADS=1\n./run\n"
    )
    assert "OPENMP_MISMATCH" in codes(diagnose(script=script))


def test_gpu_possibly_unused_requires_logs():
    script = parse_sbatch_text("#SBATCH --gres=gpu:1\n")
    # No logs provided -> cannot conclude, so no GPU finding
    assert "GPU_POSSIBLY_UNUSED" not in codes(diagnose(script=script))
    # CPU-only log present -> flag it
    findings = diagnose(script=script, log_text="Training on CPU. Done.\n")
    assert "GPU_POSSIBLY_UNUSED" in codes(findings)
    # A log mentioning CUDA clears the flag
    findings = diagnose(script=script, log_text="Using device: cuda:0\n")
    assert "GPU_POSSIBLY_UNUSED" not in codes(findings)


def test_environment_module_not_found():
    logs = scan_text("ModuleNotFoundError: No module named 'torch'\n")
    assert "MODULE_NOT_FOUND" in codes(diagnose(logs=logs))


def test_node_failure_state():
    job = JobRecord(job_id="3", state="NODE_FAIL")
    assert "NODE_FAILURE" in codes(diagnose(job=job))


def test_ordering_puts_critical_first():
    job = JobRecord(
        job_id="4",
        state="OUT_OF_MEMORY",
        requested_memory_mb=16384,
        max_rss_mb=16000,
        allocated_cpus=16,
        elapsed_seconds=3600,
        total_cpu_seconds=1800,  # also low cpu efficiency
    )
    findings = diagnose(job=job)
    assert findings[0].code == "OUT_OF_MEMORY"
    assert findings[0].severity == "critical"
