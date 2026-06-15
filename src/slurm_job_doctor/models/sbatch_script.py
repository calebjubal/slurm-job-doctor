"""Model of a parsed ``sbatch`` script.

The model keeps every original line verbatim in :attr:`SbatchScript.lines` and records,
for each ``#SBATCH`` directive, the line it came from. That lets the patcher rewrite a
single directive in place while leaving comments, blank lines, and the command body
untouched.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class SbatchDirective(BaseModel):
    """A single ``#SBATCH`` option, normalized to its long form."""

    key: str  # long option name without leading dashes, e.g. "cpus-per-task"
    value: str | None = None  # None for boolean flags like --exclusive
    raw: str  # the full original line, e.g. "#SBATCH --mem=32G"
    line_index: int  # index into SbatchScript.lines


class SbatchScript(BaseModel):
    """A parsed batch script that can be round-tripped back to text."""

    path: str | None = None
    lines: list[str] = Field(default_factory=list)
    directives: list[SbatchDirective] = Field(default_factory=list)
    shebang: str | None = None

    @property
    def directive_map(self) -> dict[str, str | None]:
        """Map of directive key to value, last occurrence winning (as Slurm resolves)."""
        result: dict[str, str | None] = {}
        for directive in self.directives:
            result[directive.key] = directive.value
        return result

    def get(self, *keys: str) -> str | None:
        """Return the value of the first present directive among ``keys``."""
        mapping = self.directive_map
        for key in keys:
            if key in mapping:
                return mapping[key]
        return None

    # --- typed convenience accessors -------------------------------------------------
    @property
    def job_name(self) -> str | None:
        return self.get("job-name")

    @property
    def partition(self) -> str | None:
        return self.get("partition")

    @property
    def account(self) -> str | None:
        return self.get("account")

    @property
    def nodes(self) -> str | None:
        return self.get("nodes")

    @property
    def ntasks(self) -> str | None:
        return self.get("ntasks")

    @property
    def cpus_per_task(self) -> str | None:
        return self.get("cpus-per-task")

    @property
    def mem(self) -> str | None:
        return self.get("mem")

    @property
    def mem_per_cpu(self) -> str | None:
        return self.get("mem-per-cpu")

    @property
    def time(self) -> str | None:
        return self.get("time")

    @property
    def gres(self) -> str | None:
        return self.get("gres")

    @property
    def gpus(self) -> str | None:
        return self.get("gpus")

    @property
    def output(self) -> str | None:
        return self.get("output")

    @property
    def error(self) -> str | None:
        return self.get("error")

    @property
    def body(self) -> list[str]:
        """Executable command lines (everything that is not blank, shebang, or comment)."""
        commands: list[str] = []
        for line in self.lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            commands.append(line)
        return commands

    @property
    def gpu_count(self) -> int | None:
        """Number of GPUs requested via ``--gres=gpu:N`` or ``--gpus=N`` (None if unset)."""
        gres = self.gres
        if gres:
            parts = gres.split(":")
            if parts and parts[0].lower() == "gpu":
                last = parts[-1]
                return int(last) if last.isdigit() else 1
        gpus = self.gpus
        if gpus:
            last = gpus.split(":")[-1]
            if last.isdigit():
                return int(last)
        return None
