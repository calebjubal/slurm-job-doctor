"""Rich terminal rendering of a report."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from slurm_job_doctor.models.report import Report

_SEVERITY_STYLE = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "cyan",
    "info": "dim",
}


def _severity_style(severity: str) -> str:
    return _SEVERITY_STYLE.get(severity, "white")


def render(report: Report, console: Console | None = None) -> None:
    console = console or Console()
    job = report.job

    if job is not None:
        header = f"[bold]Job {job.job_id}[/]"
        if job.job_name:
            header += f"  ·  {job.job_name}"
        header += f"\nState: {job.state or 'unknown'}"
        if job.exit_code:
            header += f"   Exit code: {job.exit_code}"
        if job.cpu_efficiency is not None:
            header += f"\nCPU efficiency: {job.cpu_efficiency * 100:.0f}%"
        if job.memory_utilization is not None:
            header += f"   Memory utilization: {job.memory_utilization * 100:.0f}%"
        console.print(Panel(header, title="slurm-job-doctor", border_style="blue", expand=False))

    if report.healthy:
        console.print(
            Panel(
                "No problems detected. The job's resource request looks reasonable.",
                title="Healthy",
                border_style="green",
                expand=False,
            )
        )
        return

    primary = report.primary
    style = _severity_style(primary.severity)
    console.print(
        Panel(
            f"[{style}]{primary.title}[/]\n{primary.message}",
            title=f"Primary diagnosis · {primary.severity.upper()}",
            border_style=style,
            expand=False,
        )
    )

    table = Table(title="Diagnoses", expand=False)
    table.add_column("Severity")
    table.add_column("Code")
    table.add_column("Finding")
    for diagnosis in report.diagnoses:
        diag_style = _severity_style(diagnosis.severity)
        table.add_row(
            f"[{diag_style}]{diagnosis.severity.upper()}[/]",
            diagnosis.code,
            diagnosis.title,
        )
    console.print(table)

    for diagnosis in report.diagnoses:
        if diagnosis.evidence:
            console.print(f"[bold]{diagnosis.code}[/] evidence:")
            for item in diagnosis.evidence:
                console.print(f"  • {item}")

    directives = report.directive_recommendations
    if directives:
        rec_table = Table(title="Recommended directive changes", expand=False)
        rec_table.add_column("Directive")
        rec_table.add_column("From")
        rec_table.add_column("To", style="bold green")
        rec_table.add_column("Why")
        for rec in directives:
            rec_table.add_row(rec.directive, rec.old_value or "—", rec.new_value or "—", rec.reason)
        console.print(rec_table)

    for rec in report.script_recommendations:
        console.print(f"[bold]script:[/] set {rec.directive}={rec.new_value} — {rec.reason}")

    if report.notes:
        console.print("[bold]Notes:[/]")
        for note in report.notes:
            console.print(f"  • {note.reason}")

    if report.options:
        opt_table = Table(title="Resource options (queue impact)", expand=False)
        opt_table.add_column("Option")
        opt_table.add_column("Memory")
        opt_table.add_column("Time")
        opt_table.add_column("Success")
        opt_table.add_column("Queue impact")
        for option in report.options:
            opt_table.add_row(
                option.label,
                option.mem or "—",
                option.time or "—",
                option.success_probability,
                option.queue_impact,
            )
        console.print(opt_table)

    if report.patch_output:
        console.print(
            Panel(
                f"Patched script written to [bold]{report.patch_output}[/]\n"
                f"Next: [bold]sbatch {report.patch_output}[/]",
                title="Patch",
                border_style="green",
                expand=False,
            )
        )
