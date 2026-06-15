from pathlib import Path

import pytest

from slurm_job_doctor.analysis import analyze_inputs
from slurm_job_doctor.collectors import sacct_collector
from slurm_job_doctor.collectors.command_runner import CommandResult
from slurm_job_doctor.reporting import json_report, markdown

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

# expected primary diagnosis per bundled example
CASES = {
    "oom": ("slurm-1001", "OUT_OF_MEMORY"),
    "timeout": ("slurm-1002", "TIMEOUT"),
    "low_cpu_efficiency": ("slurm-1003", "MEMORY_OVER_REQUESTED"),
    "gpu_not_used": ("slurm-1004", "GPU_POSSIBLY_UNUSED"),
}


@pytest.mark.parametrize("name,expected", [(n, e) for n, (_, e) in CASES.items()])
def test_each_example_diagnoses_as_expected(name, expected):
    prefix = CASES[name][0]
    folder = EXAMPLES / name
    report = analyze_inputs(
        sbatch=folder / "job.sbatch",
        sacct=folder / "sacct.csv",
        stdout=folder / f"{prefix}.out",
        stderr=folder / f"{prefix}.err",
    )
    assert report.primary is not None
    assert report.primary.code == expected
    # every report must render to json and markdown without error
    assert json_report.to_json(report)
    assert markdown.to_markdown(report).startswith("## slurm-job-doctor report")


def test_low_cpu_example_flags_both_cpu_and_memory():
    folder = EXAMPLES / "low_cpu_efficiency"
    report = analyze_inputs(sbatch=folder / "job.sbatch", sacct=folder / "sacct.csv")
    codes = {d.code for d in report.diagnoses}
    assert {"MEMORY_OVER_REQUESTED", "CPU_OVER_REQUESTED"} <= codes


def test_sacct_collector_with_mock_runner():
    text = (EXAMPLES / "oom" / "sacct.csv").read_text(encoding="utf-8")
    captured = {}

    def fake_runner(cmd):
        captured["cmd"] = cmd
        return CommandResult(0, text, "")

    out = sacct_collector.collect("1001", runner=fake_runner)
    assert "OUT_OF_MEMORY" in out
    assert captured["cmd"][0] == "sacct"
    assert "--jobs" in captured["cmd"]


def test_sacct_collector_raises_on_failure():
    def failing(cmd):
        return CommandResult(1, "", "sacct: invalid job id")

    with pytest.raises(RuntimeError, match="sacct failed"):
        sacct_collector.collect("999", runner=failing)


def test_analyze_inputs_uses_sacct_runner_for_job_id():
    text = (EXAMPLES / "oom" / "sacct.csv").read_text(encoding="utf-8")
    report = analyze_inputs(job_id="1001", sacct_runner=lambda job_id: text)
    assert report.primary.code == "OUT_OF_MEMORY"


def test_malformed_sacct_does_not_crash():
    # a row whose columns are shifted so TotalCPU holds a TRES string
    bad = "JobID|State|TotalCPU|Elapsed\n1|COMPLETED|cpu=8,mem=16G|00:10:00\n"
    from slurm_job_doctor.parsers.sacct_parser import parse_sacct_text

    (record,) = parse_sacct_text(bad)
    assert record.total_cpu_seconds is None  # junk degrades to None, no exception
    assert record.elapsed_seconds == 600
