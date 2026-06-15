# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-06-15

First usable release: the rule-based doctor. Parses local `sbatch` / `sacct` / log
files (no Slurm required), diagnoses OOM, timeout, and CPU/memory/GPU inefficiency,
recommends fixes, and emits a patched `.doctor.sbatch`.

### Added
- Repo scaffold: packaging (`pyproject.toml`), license, `.gitignore`, `Makefile`,
  `src/` layout, and the development roadmap.
- `parsers.unit_parser`: normalize Slurm memory (`16G` → 16384 MiB) and time
  (`1-02:00:00` → 93600 s) strings, plus formatters for writing them back.
- `models.SbatchScript` + `parsers.sbatch_parser`: extract `#SBATCH` directives
  (long and short forms) while preserving comments, blank lines, body, and order;
  derive GPU count from `--gres`/`--gpus`.
- `models.JobRecord` + `parsers.sacct_parser`: parse `--parsable2`/CSV `sacct`
  output, merging a job's allocation, `.batch`, and step rows into one record;
  scale per-cpu/per-node `ReqMem`, expand compact nodelists, derive CPU efficiency,
  memory utilization, and GPU count from TRES.
- `diagnosis.patterns` + `parsers.log_parser` + `models.LogEvidence`: scan
  stdout/stderr for known failure signatures (CUDA/host OOM, walltime, module/conda,
  import, disk, segfault) with first-match-wins precedence and per-pattern capping.
- `diagnosis.engine` + rule modules (oom, timeout, memory/cpu efficiency, gpu,
  environment, state) producing severity-ranked `Diagnosis` findings; `config.DoctorConfig`
  for safety factors and thresholds, loadable from `.doctor.yml` (adds `pyyaml`).
- `recommenders` (memory, runtime, cpu, gpu) + `queue_impact` estimator turning
  diagnoses into `Recommendation`s (e.g. OOM → bump `--mem` to peak RSS × 1.5) and
  Recommended/Conservative `ResourceOption`s with success-probability and queue-impact
  labels. Honors `max_mem_gb`/`max_walltime_hours` caps.
- `patcher` (`sbatch_patcher` + `safety`): rewrite `#SBATCH` directives in place
  (preserving body, comments, inline notes, and order), insert missing directives, apply
  the OpenMP fix, and emit `<name>.doctor.sbatch` — or back up to `<name>.bak` and
  overwrite with `--apply`. Safety layer drops any edit that would shrink memory after
  an OOM (or walltime after a timeout).
- `analysis` pipeline + `collectors` (sacct/file/command runner) + `reporting`
  (terminal/JSON/markdown) + `cli` (`analyze`, `patch`, `version`; roadmap stubs for
  `monitor`/`collect`/`train`/`dashboard`).
- Four runnable example jobs (`examples/oom`, `timeout`, `low_cpu_efficiency`,
  `gpu_not_used`) and docs (`architecture`, `cli`, `diagnosis-rules`, `examples`).

### Fixed
- `sacct_parser` no longer raises on a malformed/misaligned field (e.g. a TRES string
  landing in `TotalCPU`); unparseable values degrade to `None`.
- GPU-usage detection no longer treats "no CUDA device" log lines as evidence the GPU
  was used; it now looks for positive GPU-use signals only.
