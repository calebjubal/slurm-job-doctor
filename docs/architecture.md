# Architecture

`slurm-job-doctor` is a one-way pipeline. Each layer has a single job and depends only
on the layers above it, which keeps every stage independently testable.

```
            ┌─────────────┐
   evidence │ collectors  │  run sacct / read local files (mockable I/O)
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │  parsers    │  raw text → typed models
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │   models    │  JobRecord, SbatchScript, LogEvidence, …
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │ diagnosis   │  rules → list[Diagnosis] (severity-ranked)
            └──────┬──────┘
                   ▼
            ┌─────────────┐
            │ recommenders│  diagnoses → Recommendation + queue options
            └──────┬──────┘
                   ▼
        ┌──────────┴──────────┐
        ▼                     ▼
 ┌─────────────┐       ┌─────────────┐
 │   patcher   │       │  reporting  │  terminal / json / markdown
 └─────────────┘       └─────────────┘
```

## Layers

- **collectors** — the only code that touches the outside world. `command_runner` wraps
  subprocess calls; `sacct_collector` builds the `sacct` command; `file_collector` reads
  local files. Every collector takes an injectable runner so tests never need Slurm.
- **parsers** — pure functions from text to models: `unit_parser` (memory/time
  normalization), `sbatch_parser`, `sacct_parser`, and `log_parser`.
- **models** — Pydantic models passed between layers so everything speaks the same
  language. Derived metrics (CPU efficiency, memory utilization, GPU count) live here.
- **diagnosis** — independent rule modules, each returning `list[Diagnosis]`. The engine
  de-duplicates by code and ranks by severity. `patterns.py` holds the log regexes.
- **recommenders** — translate diagnoses into `Recommendation`s and `ResourceOption`s.
  `config.DoctorConfig` supplies safety factors and caps.
- **patcher** — rewrites `#SBATCH` directives in place behind a `safety` guard.
- **reporting** — three renderers over the same `Report` object.

`analysis.py` wires these together: `analyze_inputs(...)` is the single entry point the
CLI (and any future API) calls.

## Why this shape

- Parsers never make decisions; rules never parse text. A bug is easy to localize.
- The collector boundary means the whole pipeline runs on a laptop with no Slurm.
- Adding a failure mode is usually a new `diagnosis/` module plus a `recommenders/` case,
  with no churn elsewhere.
