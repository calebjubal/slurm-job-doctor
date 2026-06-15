"""Models for resource recommendations and queue-impact options."""

from __future__ import annotations

from pydantic import BaseModel


class Recommendation(BaseModel):
    """A single suggested change.

    ``kind`` distinguishes a ``#SBATCH`` directive change (consumed by the patcher)
    from script-body advice or a free-form note.
    """

    directive: str = ""  # display form, e.g. "--mem"; empty for notes
    old_value: str | None = None
    new_value: str | None = None  # None means "remove" for directive kind
    reason: str = ""
    kind: str = "directive"  # "directive" | "script" | "note"

    @property
    def key(self) -> str:
        """The bare directive name the patcher edits, e.g. ``mem`` for ``--mem``."""
        return self.directive.lstrip("-")


class ResourceOption(BaseModel):
    """One point on the safety/queue-cost trade-off, shown by the queue estimator."""

    label: str  # "Recommended" / "Conservative"
    mem: str | None = None
    time: str | None = None
    success_probability: str  # low / medium / high / very high
    queue_impact: str  # low / medium / high
    note: str | None = None
