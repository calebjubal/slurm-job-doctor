from slurm_job_doctor.diagnosis.engine import diagnose
from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.models.recommendation import Recommendation
from slurm_job_doctor.parsers.sbatch_parser import parse_sbatch_text
from slurm_job_doctor.patcher.sbatch_patcher import (
    patch_file,
    patch_script_text,
    patch_text,
)
from slurm_job_doctor.recommenders.engine import recommend

OOM_SCRIPT = """#!/bin/bash
#SBATCH --job-name=train_model
#SBATCH --mem=16G
#SBATCH --cpus-per-task=8
# keep this comment
module load cuda
python train.py
"""


def test_oom_patch_changes_mem_and_preserves_body():
    job = JobRecord(
        job_id="123456",
        state="OUT_OF_MEMORY",
        requested_memory_mb=16384,
        max_rss_mb=15700,
    )
    script = parse_sbatch_text(OOM_SCRIPT, path="train.sbatch")
    diagnoses = diagnose(job=job, script=script)
    recs = recommend(diagnoses, job=job, script=script)
    result = patch_text(script, recs.items, diagnoses)

    assert "mem" in result.changed
    assert "#SBATCH --mem=23G" in result.patched_text
    # body and comments preserved
    assert "# keep this comment" in result.patched_text
    assert "module load cuda" in result.patched_text
    assert "python train.py" in result.patched_text
    # shebang stays first
    assert result.patched_text.splitlines()[0] == "#!/bin/bash"
    assert result.diff  # a non-empty unified diff


def test_missing_directive_is_inserted_after_last_sbatch():
    script = parse_sbatch_text("#!/bin/bash\n#SBATCH --mem=8G\n./run\n")
    rec = Recommendation(directive="--time", old_value=None, new_value="01:00:00")
    result = patch_text(script, [rec])
    lines = result.patched_text.splitlines()
    assert "#SBATCH --time=01:00:00" in lines
    # inserted within the directive block, before the command
    assert lines.index("#SBATCH --time=01:00:00") < lines.index("./run")


def test_openmp_script_recommendation_replaces_line():
    text = "#!/bin/bash\n#SBATCH --cpus-per-task=32\nexport OMP_NUM_THREADS=1\npython x.py\n"
    rec = Recommendation(
        directive="OMP_NUM_THREADS",
        old_value="1",
        new_value="${SLURM_CPUS_PER_TASK:-1}",
        kind="script",
    )
    result = patch_script_text(text, [rec])
    assert "export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}" in result.patched_text
    assert "export OMP_NUM_THREADS=1" not in result.patched_text


def test_inline_comment_preserved_on_changed_directive():
    script = parse_sbatch_text("#SBATCH --mem=16G  # bump later\n")
    rec = Recommendation(directive="--mem", old_value="16G", new_value="32G")
    result = patch_text(script, [rec])
    assert "#SBATCH --mem=32G  # bump later" in result.patched_text


def test_safety_blocks_lowering_memory_after_oom():
    script = parse_sbatch_text("#SBATCH --mem=16G\n")
    bad = Recommendation(directive="--mem", old_value="16G", new_value="8G")
    diagnoses = [Diagnosis(code="OUT_OF_MEMORY", category="memory", severity="critical",
                           title="oom", message="oom")]
    result = patch_text(script, [bad], diagnoses)
    # the unsafe lowering must be dropped
    assert "mem" not in result.changed
    assert "#SBATCH --mem=8G" not in result.patched_text


def test_patch_file_writes_doctor_sibling(tmp_path):
    src = tmp_path / "train.sbatch"
    src.write_text(OOM_SCRIPT, encoding="utf-8")
    rec = Recommendation(directive="--mem", old_value="16G", new_value="24G")
    result = patch_file(src, [rec])
    assert result.output_path.endswith("train.doctor.sbatch")
    assert (tmp_path / "train.doctor.sbatch").exists()
    # original untouched
    assert "--mem=16G" in src.read_text()


def test_patch_file_apply_creates_backup(tmp_path):
    src = tmp_path / "job.sbatch"
    src.write_text("#SBATCH --mem=16G\n./run\n", encoding="utf-8")
    rec = Recommendation(directive="--mem", old_value="16G", new_value="24G")
    result = patch_file(src, [rec], apply=True)
    assert result.applied
    assert (tmp_path / "job.sbatch.bak").exists()
    assert "--mem=16G" in (tmp_path / "job.sbatch.bak").read_text()
    assert "--mem=24G" in src.read_text()
