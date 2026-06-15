# Diagnosis rules

Each rule lives in its own module under `diagnosis/` and returns zero or more
`Diagnosis` findings. The engine de-duplicates by code and sorts by severity, so the
first finding is always the most serious.

## Failure diagnoses

| Code | Trigger | Severity | Recommendation |
| --- | --- | --- | --- |
| `OUT_OF_MEMORY` | state `OUT_OF_MEMORY`, or an `oom-kill` log line | critical | `--mem` → `max(MaxRSS×1.5, ReqMem×1.25)`, rounded up to a whole GiB |
| `CUDA_OUT_OF_MEMORY` | `CUDA out of memory` in logs | critical | note: reduce batch size / use checkpointing (host `--mem` unchanged) |
| `TIMEOUT` | state `TIMEOUT`, or `DUE TO TIME LIMIT` in logs | critical | `--time` → `Elapsed×1.5`; suggest checkpointing |
| `MODULE_NOT_FOUND` / `IMPORT_ERROR` | Python import failures in logs | high | environment fix guidance |
| `CONDA_NOT_FOUND` / `MODULE_LOAD_ERROR` | conda / Lmod failures | high | environment fix guidance |
| `INVALID_PARTITION` / `INVALID_ACCOUNT` | submit-time errors | high | check `sinfo` / `sacctmgr` |
| `NODE_FAILURE` / `BOOT_FAIL` / `DEADLINE` / `PREEMPTED` / `JOB_CANCELLED` / `JOB_FAILED` | other non-clean states | medium–high | state-specific guidance |

## Efficiency diagnoses

| Code | Trigger | Severity | Recommendation |
| --- | --- | --- | --- |
| `MEMORY_OVER_REQUESTED` | `MaxRSS < 0.4 × ReqMem` (non-OOM) | low | `--mem` → `MaxRSS×1.3` |
| `MEMORY_NEAR_LIMIT` | `MaxRSS ≥ 0.9 × ReqMem` (non-OOM) | medium | small headroom bump |
| `CPU_OVER_REQUESTED` | CPU efficiency `< 0.3` with `>1` CPU | low | `--cpus-per-task` → average busy cores |
| `OPENMP_MISMATCH` | `--cpus-per-task ≥ 2` but `OMP_NUM_THREADS=1` | medium | set `OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}` |
| `GPU_POSSIBLY_UNUSED` | GPU requested, logs present, no GPU-use evidence | medium | note: drop the GPU request if CPU-only |

Thresholds and factors (`0.4`, `0.3`, `0.9`, `1.25`, `1.5`, `1.3`) come from
`config.DoctorConfig` and can be overridden per site in `.doctor.yml`.

## Safety rules

These are enforced both in the recommenders and again in `patcher/safety.py`:

- Never recommend **less** memory after an `OUT_OF_MEMORY`.
- Never recommend **less** walltime after a `TIMEOUT`.
- Only flag an unused GPU when logs were actually provided.
- Recommendations are capped by `max_mem_gb` / `max_walltime_hours` when configured.
- The patcher writes `<name>.doctor.sbatch` by default and only overwrites with
  `--apply`, always creating a `.bak` first.
