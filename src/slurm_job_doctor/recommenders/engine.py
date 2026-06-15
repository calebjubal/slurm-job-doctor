"""Assemble all recommender outputs and the queue-impact options."""

from __future__ import annotations

from dataclasses import dataclass, field

from slurm_job_doctor.config import DoctorConfig
from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.models.recommendation import Recommendation, ResourceOption
from slurm_job_doctor.models.sbatch_script import SbatchScript
from slurm_job_doctor.recommenders import cpu, gpu, memory, queue_impact, runtime
from slurm_job_doctor.recommenders.context import RecommendationContext


@dataclass
class Recommendations:
    """Everything the recommender layer produces for a job."""

    items: list[Recommendation] = field(default_factory=list)
    options: list[ResourceOption] = field(default_factory=list)

    @property
    def directives(self) -> list[Recommendation]:
        return [item for item in self.items if item.kind == "directive"]


def recommend(
    diagnoses: list[Diagnosis],
    job: JobRecord | None = None,
    script: SbatchScript | None = None,
    *,
    config: DoctorConfig | None = None,
) -> Recommendations:
    """Produce directive changes, script advice, notes, and queue-impact options."""
    ctx = RecommendationContext(
        diagnoses=diagnoses,
        job=job,
        script=script,
        config=config or DoctorConfig(),
    )

    items: list[Recommendation] = []
    for module in (memory, runtime, cpu, gpu):
        items.extend(module.recommend(ctx))

    options = queue_impact.estimate(ctx, items)
    return Recommendations(items=items, options=options)
