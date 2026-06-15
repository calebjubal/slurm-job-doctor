import json
from pathlib import Path

from typer.testing import CliRunner

from slurm_job_doctor.cli import app

runner = CliRunner()
EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def test_analyze_oom_json():
    result = runner.invoke(
        app,
        [
            "analyze",
            "--sacct",
            str(EXAMPLES / "oom" / "sacct.csv"),
            "--stderr",
            str(EXAMPLES / "oom" / "slurm-1001.err"),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["primary_diagnosis"] == "OUT_OF_MEMORY"
    assert any(r["directive"] == "--mem" for r in data["recommendations"])


def test_analyze_terminal_runs():
    result = runner.invoke(
        app, ["analyze", "--sacct", str(EXAMPLES / "timeout" / "sacct.csv")]
    )
    assert result.exit_code == 0
    assert "TIMEOUT" in result.stdout


def test_analyze_requires_some_input():
    result = runner.invoke(app, ["analyze"])
    assert result.exit_code == 2


def test_patch_writes_doctor_file(tmp_path):
    sbatch = tmp_path / "job.sbatch"
    sbatch.write_text((EXAMPLES / "oom" / "job.sbatch").read_text(), encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "patch",
            "--sbatch",
            str(sbatch),
            "--sacct",
            str(EXAMPLES / "oom" / "sacct.csv"),
            "--stderr",
            str(EXAMPLES / "oom" / "slurm-1001.err"),
        ],
    )
    assert result.exit_code == 0
    patched = tmp_path / "job.doctor.sbatch"
    assert patched.exists()
    assert "#SBATCH --mem=24G" in patched.read_text()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0


def test_monitor_is_roadmap_stub():
    result = runner.invoke(app, ["monitor", "--job-id", "1"])
    assert result.exit_code == 1
