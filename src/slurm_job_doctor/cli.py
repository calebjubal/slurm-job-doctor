"""Command-line entry point for slurm-job-doctor."""

from __future__ import annotations

import enum
from pathlib import Path

import typer
from rich.console import Console

from slurm_job_doctor import __version__
from slurm_job_doctor.analysis import analyze_inputs
from slurm_job_doctor.collectors import sacct_collector
from slurm_job_doctor.models.report import Report
from slurm_job_doctor.patcher.sbatch_patcher import patch_file
from slurm_job_doctor.reporting import json_report, markdown, terminal

app = typer.Typer(
    add_completion=False,
    help="Diagnose failed or inefficient Slurm jobs and right-size resource requests.",
    no_args_is_help=True,
)
console = Console()
err_console = Console(stderr=True)


class OutputFormat(enum.StrEnum):
    terminal = "terminal"
    json = "json"
    markdown = "markdown"


def _emit(report: Report, fmt: OutputFormat) -> None:
    if fmt is OutputFormat.json:
        print(json_report.to_json(report))
    elif fmt is OutputFormat.markdown:
        print(markdown.to_markdown(report))
    else:
        terminal.render(report, console)


def _require_some_input(job_id, sbatch, sacct, stdout, stderr) -> None:
    if not any([job_id, sbatch, sacct, stdout, stderr]):
        err_console.print(
            "[red]Nothing to analyze.[/] Provide --job-id, or one of "
            "--sbatch / --sacct / --stdout / --stderr."
        )
        raise typer.Exit(code=2)


@app.command()
def analyze(
    job_id: str = typer.Option(None, "--job-id", help="Completed job id (uses sacct)."),
    sbatch: Path = typer.Option(None, "--sbatch", exists=True, dir_okay=False),
    sacct: Path = typer.Option(None, "--sacct", exists=True, dir_okay=False, help="sacct dump."),
    stdout: Path = typer.Option(None, "--stdout", exists=True, dir_okay=False),
    stderr: Path = typer.Option(None, "--stderr", exists=True, dir_okay=False),
    config: Path = typer.Option(None, "--config", exists=True, dir_okay=False, help=".doctor.yml"),
    fmt: OutputFormat = typer.Option(OutputFormat.terminal, "--format"),
    do_patch: bool = typer.Option(False, "--patch", help="Also write <name>.doctor.sbatch."),
) -> None:
    """Analyze a completed job and recommend fixes."""
    _require_some_input(job_id, sbatch, sacct, stdout, stderr)
    report = analyze_inputs(
        job_id=job_id,
        sbatch=sbatch,
        sacct=sacct,
        stdout=stdout,
        stderr=stderr,
        config_path=config,
        sacct_runner=sacct_collector.collect,
    )

    if do_patch and sbatch is not None and report.directive_recommendations:
        result = patch_file(sbatch, report.recommendations, report.diagnoses)
        report.patch_output = result.output_path
        report.patch_diff = result.diff

    _emit(report, fmt)


@app.command()
def patch(
    sbatch: Path = typer.Option(..., "--sbatch", exists=True, dir_okay=False),
    job_id: str = typer.Option(None, "--job-id"),
    sacct: Path = typer.Option(None, "--sacct", exists=True, dir_okay=False),
    stdout: Path = typer.Option(None, "--stdout", exists=True, dir_okay=False),
    stderr: Path = typer.Option(None, "--stderr", exists=True, dir_okay=False),
    config: Path = typer.Option(None, "--config", exists=True, dir_okay=False),
    output: Path = typer.Option(None, "--output", "-o", dir_okay=False),
    apply: bool = typer.Option(False, "--apply", help="Overwrite in place (backs up to .bak)."),
) -> None:
    """Generate a patched sbatch script from a job's diagnosis."""
    report = analyze_inputs(
        job_id=job_id,
        sbatch=sbatch,
        sacct=sacct,
        stdout=stdout,
        stderr=stderr,
        config_path=config,
        sacct_runner=sacct_collector.collect,
    )
    if not report.directive_recommendations:
        console.print("[green]No directive changes recommended — script left as is.[/]")
        raise typer.Exit(code=0)

    result = patch_file(
        sbatch,
        report.recommendations,
        report.diagnoses,
        output=output,
        apply=apply,
    )
    report.patch_output = result.output_path
    report.patch_diff = result.diff

    terminal.render(report, console)
    if result.diff:
        console.print(result.diff, highlight=False)
    if result.backup_path:
        console.print(f"[dim]Backup saved to {result.backup_path}[/]")


def _roadmap_stub(name: str, milestone: str) -> None:
    err_console.print(
        f"[yellow]'{name}' is planned for {milestone}.[/] "
        "See docs/roadmap.md for the development plan."
    )
    raise typer.Exit(code=1)


@app.command()
def monitor(job_id: str = typer.Option(..., "--job-id")) -> None:
    """Monitor a running job (live sstat warnings)."""
    _roadmap_stub("monitor", "v0.2.0")


@app.command()
def collect(
    since: str = typer.Option(None, "--since"),
    output: Path = typer.Option(None, "--output"),
) -> None:
    """Build a dataset from historical jobs."""
    _roadmap_stub("collect", "v0.3.0")


@app.command()
def train(
    target: str = typer.Argument("memory"),
    input: Path = typer.Option(None, "--input"),
    output: Path = typer.Option(None, "--output"),
) -> None:
    """Train a resource-prediction model."""
    _roadmap_stub("train", "v0.4.0")


@app.command()
def dashboard() -> None:
    """Launch the Streamlit dashboard."""
    _roadmap_stub("dashboard", "v0.5.0")


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(__version__)


if __name__ == "__main__":  # pragma: no cover
    app()
