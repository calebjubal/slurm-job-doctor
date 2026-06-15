from slurm_job_doctor.parsers.log_parser import scan_files, scan_text

OOM_LOG = """Epoch 1 starting
slurmstepd: error: Detected 1 oom-kill event(s) in StepId=123456.batch.
Some of your processes may have been killed by the cgroup out-of-memory handler.
"""

CUDA_LOG = """Traceback (most recent call last):
  File "train.py", line 42, in <module>
RuntimeError: CUDA out of memory. Tried to allocate 2.00 GiB
"""

TIMEOUT_LOG = "slurmstepd: error: *** JOB 123456 CANCELLED AT 2025-01-01 DUE TO TIME LIMIT ***\n"

ENV_LOG = """conda: command not found
Traceback (most recent call last):
ModuleNotFoundError: No module named 'torch'
"""

CLEAN_LOG = "Job started\nProcessing batch 1/100\nAll done. Exit 0.\n"


def test_detects_oom_kill():
    evidence = scan_text(OOM_LOG, source="slurm.err")
    assert evidence.has("oom_kill")
    assert evidence.has_category("memory")
    assert evidence.severity == "critical"
    assert any("oom-kill" in line for line in evidence.important_lines)


def test_cuda_oom_does_not_also_flag_host_oom():
    evidence = scan_text(CUDA_LOG)
    assert evidence.has("cuda_oom")
    # the specific CUDA pattern wins; the generic host-OOM pattern must not also fire
    assert not evidence.has("oom_kill")


def test_detects_timeout():
    evidence = scan_text(TIMEOUT_LOG)
    assert evidence.has("timeout")
    assert evidence.severity == "critical"


def test_detects_environment_errors():
    evidence = scan_text(ENV_LOG)
    assert evidence.has("conda_missing")
    assert evidence.has("module_not_found")
    assert "environment" in evidence.categories


def test_clean_log_has_no_matches():
    evidence = scan_text(CLEAN_LOG)
    assert evidence.matches == []
    assert evidence.severity == "none"


def test_match_capping():
    spammy = "\n".join(["RuntimeError: CUDA out of memory"] * 50)
    evidence = scan_text(spammy)
    assert len(evidence.lines_for("cuda_oom")) == 5


def test_scan_files_merges_and_records_source(tmp_path):
    err = tmp_path / "slurm.err"
    err.write_text(OOM_LOG, encoding="utf-8")
    out = tmp_path / "slurm.out"
    out.write_text(CLEAN_LOG, encoding="utf-8")
    evidence = scan_files([out, err, tmp_path / "missing.log"])
    assert evidence.has("oom_kill")
    sources = {m.source for m in evidence.matches}
    assert "slurm.err" in sources
