"""The top-level object every report format renders."""

from __future__ import annotations

from pydantic import BaseModel, Field

from slurm_job_doctor.models.diagnosis import Diagnosis
from slurm_job_doctor.models.job_record import JobRecord
from slurm_job_doctor.models.recommendation import Recommendation, ResourceOption


class Report(BaseModel):
    job: JobRecord | None = None
    script_path: str | None = None
    diagnoses: list[Diagnosis] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    options: list[ResourceOption] = Field(default_factory=list)
    patch_output: str | None = None  # path of a generated .doctor.sbatch, if any
    patch_diff: str | None = None

    @property
    def primary(self) -> Diagnosis | None:
        return self.diagnoses[0] if self.diagnoses else None

    @property
    def healthy(self) -> bool:
        return not self.diagnoses

    @property
    def directive_recommendations(self) -> list[Recommendation]:
        return [
            r for r in self.recommendations if r.kind == "directive" and r.new_value is not None
        ]

    @property
    def script_recommendations(self) -> list[Recommendation]:
        return [r for r in self.recommendations if r.kind == "script"]

    @property
    def notes(self) -> list[Recommendation]:
        return [r for r in self.recommendations if r.kind == "note"]
