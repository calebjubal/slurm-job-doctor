from slurm_job_doctor.diagnosis.engine import diagnose
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.parsers.sbatch_parser import parse_sbatch_text
from slurm_job_doctor.recommenders.engine import recommend


def directive(recs, name):
    return next((r for r in recs.items if r.directive == name), None)


def test_oom_recommends_more_memory_like_readme():
    job = JobRecord(
        job_id="123456",
        state="OUT_OF_MEMORY",
        requested_memory_mb=16384,
        max_rss_mb=15700,
        allocated_cpus=8,
    )
    script = parse_sbatch_text("#!/bin/bash\n#SBATCH --mem=16G\npython train.py\n")
    diagnoses = diagnose(job=job, script=script)
    recs = recommend(diagnoses, job=job, script=script)
    mem = directive(recs, "--mem")
    assert mem is not None
    assert mem.old_value == "16G"
    # max(15700*1.5, 16384*1.25) = 23550 MiB -> round up to 23 GiB (≈ the README's "24 GB")
    assert mem.new_value == "23G"


def test_oom_never_lowers_memory():
    job = JobRecord(job_id="1", state="OUT_OF_MEMORY", requested_memory_mb=16384, max_rss_mb=2000)
    diagnoses = diagnose(job=job)
    recs = recommend(diagnoses, job=job)
    mem = directive(recs, "--mem")
    # even with low RSS, an OOM must not produce a smaller request
    assert mem is not None
    from slurm_job_doctor.parsers.unit_parser import parse_memory_mb

    assert parse_memory_mb(mem.new_value) > 16384


def test_timeout_recommends_more_time_like_readme():
    job = JobRecord(job_id="2", state="TIMEOUT", elapsed_seconds=7200, timelimit_seconds=7200)
    script = parse_sbatch_text("#!/bin/bash\n#SBATCH --time=02:00:00\n./run\n")
    diagnoses = diagnose(job=job, script=script)
    recs = recommend(diagnoses, job=job, script=script)
    time_rec = directive(recs, "--time")
    assert time_rec is not None
    assert time_rec.old_value == "02:00:00"
    assert time_rec.new_value == "03:00:00"  # 7200 * 1.5 = 3h


def test_memory_over_request_trims():
    job = JobRecord(
        job_id="3",
        state="COMPLETED",
        requested_memory_mb=32768,
        max_rss_mb=4096,
        allocated_cpus=1,
    )
    diagnoses = diagnose(job=job)
    recs = recommend(diagnoses, job=job)
    mem = directive(recs, "--mem")
    assert mem is not None
    from slurm_job_doctor.parsers.unit_parser import parse_memory_mb

    assert parse_memory_mb(mem.new_value) < 32768  # 4096*1.3 -> 6 GiB


def test_low_cpu_efficiency_lowers_cpus():
    job = JobRecord(
        job_id="4",
        state="COMPLETED",
        allocated_cpus=16,
        elapsed_seconds=3600,
        total_cpu_seconds=3600,  # ~1 busy core
    )
    diagnoses = diagnose(job=job)
    recs = recommend(diagnoses, job=job)
    cpus = directive(recs, "--cpus-per-task")
    assert cpus is not None
    assert int(cpus.new_value) < 16


def test_openmp_mismatch_is_a_script_recommendation():
    script = parse_sbatch_text("#!/bin/bash\n#SBATCH --cpus-per-task=32\nexport OMP_NUM_THREADS=1\n")
    diagnoses = diagnose(script=script)
    recs = recommend(diagnoses, script=script)
    omp = next((r for r in recs.items if r.directive == "OMP_NUM_THREADS"), None)
    assert omp is not None
    assert omp.kind == "script"
    assert omp.new_value == "${SLURM_CPUS_PER_TASK:-1}"


def test_queue_impact_offers_recommended_and_conservative_on_oom():
    job = JobRecord(
        job_id="5",
        state="OUT_OF_MEMORY",
        requested_memory_mb=16384,
        max_rss_mb=15700,
    )
    script = parse_sbatch_text("#SBATCH --mem=16G\n")
    diagnoses = diagnose(job=job, script=script)
    recs = recommend(diagnoses, job=job, script=script)
    labels = [o.label for o in recs.options]
    assert labels == ["Recommended", "Conservative"]
    recommended = recs.options[0]
    conservative = recs.options[1]
    assert recommended.success_probability == "high"
    assert conservative.success_probability == "very high"
    # the conservative option requests at least as much memory as the recommended one
    from slurm_job_doctor.parsers.unit_parser import parse_memory_mb

    assert parse_memory_mb(conservative.mem) >= parse_memory_mb(recommended.mem)


def test_mem_per_cpu_script_targets_mem_per_cpu_on_oom():
    job = JobRecord(
        job_id="7",
        state="OUT_OF_MEMORY",
        requested_memory_mb=16384,
        max_rss_mb=15700,
        allocated_cpus=8,
    )
    script = parse_sbatch_text(
        "#!/bin/bash\n#SBATCH --cpus-per-task=8\n#SBATCH --mem-per-cpu=2G\npython t.py\n"
    )
    diagnoses = diagnose(job=job, script=script)
    recs = recommend(diagnoses, job=job, script=script)
    # must NOT introduce a conflicting --mem; should bump --mem-per-cpu instead
    assert directive(recs, "--mem") is None
    mpc = directive(recs, "--mem-per-cpu")
    assert mpc is not None
    assert mpc.old_value == "2G"

    # and the patched script must not contain both directives
    from slurm_job_doctor.patcher.sbatch_patcher import patch_text

    patched = patch_text(script, recs.items, diagnoses).patched_text
    assert "--mem-per-cpu=" in patched
    assert "--mem=" not in patched.replace("--mem-per-cpu=", "")


def test_clean_job_has_no_directive_changes():
    job = JobRecord(
        job_id="6",
        state="COMPLETED",
        requested_memory_mb=8192,
        max_rss_mb=6000,  # ~73% utilization, healthy
        allocated_cpus=4,
        elapsed_seconds=3600,
        total_cpu_seconds=13000,  # ~90% efficiency
    )
    diagnoses = diagnose(job=job)
    recs = recommend(diagnoses, job=job)
    assert recs.directives == []
