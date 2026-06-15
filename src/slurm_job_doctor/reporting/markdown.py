"""Markdown rendering of a report, suitable for a GitHub issue or PR comment."""

from __future__ import annotations

from slurm_job_doctor.models.report import Report


def to_markdown(report: Report) -> str:
    lines: list[str] = ["## slurm-job-doctor report", ""]

    job = report.job
    if job is not None:
        lines.append(f"**Job:** {job.job_id}" + (f" ({job.job_name})" if job.job_name else ""))
        if job.state:
            lines.append(f"**State:** {job.state}")
        if job.exit_code:
            lines.append(f"**Exit code:** {job.exit_code}")
        lines.append("")

    if report.healthy:
        lines.append("No problems detected — the job's resource request looks reasonable.")
        return "\n".join(lines) + "\n"

    primary = report.primary
    lines.append("### Diagnosis")
    lines.append("")
    lines.append(f"**{primary.title}** ({primary.severity})")
    lines.append("")
    lines.append(primary.message)
    lines.append("")

    if any(d.evidence for d in report.diagnoses):
        lines.append("### Evidence")
        lines.append("")
        for diagnosis in report.diagnoses:
            for item in diagnosis.evidence:
                lines.append(f"- {item}")
        lines.append("")

    directives = report.directive_recommendations
    if directives:
        lines.append("### Recommended patch")
        lines.append("")
        lines.append("```diff")
        for rec in directives:
            old = rec.old_value if rec.old_value is not None else "(unset)"
            lines.append(f"- #SBATCH {rec.directive}={old}")
            lines.append(f"+ #SBATCH {rec.directive}={rec.new_value}")
        lines.append("```")
        lines.append("")

    if report.notes:
        lines.append("### Notes")
        lines.append("")
        for note in report.notes:
            lines.append(f"- {note.reason}")
        lines.append("")

    if report.options:
        lines.append("### Resource options")
        lines.append("")
        lines.append("| Option | Memory | Time | Success | Queue impact |")
        lines.append("| --- | --- | --- | --- | --- |")
        for option in report.options:
            lines.append(
                f"| {option.label} | {option.mem or '—'} | {option.time or '—'} "
                f"| {option.success_probability} | {option.queue_impact} |"
            )
        lines.append("")

    if report.patch_output:
        lines.append("### Next step")
        lines.append("")
        lines.append("```bash")
        lines.append(f"sbatch {report.patch_output}")
        lines.append("```")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
