"""JSON rendering of a report, intended for automation."""

from __future__ import annotations

import json

from slurm_job_doctor.models.report import Report


def to_dict(report: Report) -> dict:
    job = report.job
    job_dict = None
    if job is not None:
        job_dict = job.model_dump()
        # surface derived metrics that are properties (not stored fields)
        job_dict["cpu_efficiency"] = job.cpu_efficiency
        job_dict["memory_utilization"] = job.memory_utilization

    return {
        "healthy": report.healthy,
        "primary_diagnosis": report.primary.code if report.primary else None,
        "job": job_dict,
        "diagnoses": [d.model_dump() for d in report.diagnoses],
        "recommendations": [r.model_dump() for r in report.recommendations],
        "options": [o.model_dump() for o in report.options],
        "patch_output": report.patch_output,
    }


def to_json(report: Report, indent: int = 2) -> str:
    return json.dumps(to_dict(report), indent=indent)
