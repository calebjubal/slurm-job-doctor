# Worked examples

The `examples/` directory ships four self-contained failed/inefficient jobs. Each folder
has a `job.sbatch`, an `sacct.csv` dump, and `slurm-<id>.out` / `.err` logs, so you can
run the full tool with no Slurm install.

| Folder | Job | What the doctor finds |
| --- | --- | --- |
| `oom/` | 1001 | `OUT_OF_MEMORY` → bump `--mem` 16G → 24G |
| `timeout/` | 1002 | `TIMEOUT` → bump `--time` 01:00:00 → 01:31:00 |
| `low_cpu_efficiency/` | 1003 | `MEMORY_OVER_REQUESTED` + `CPU_OVER_REQUESTED` |
| `gpu_not_used/` | 1004 | `GPU_POSSIBLY_UNUSED` (ran on CPU) |

## Run one

```bash
slurm-doctor analyze \
  --sbatch examples/oom/job.sbatch \
  --sacct  examples/oom/sacct.csv \
  --stdout examples/oom/slurm-1001.out \
  --stderr examples/oom/slurm-1001.err
```

## Generate a patched script

```bash
slurm-doctor patch \
  --sbatch examples/oom/job.sbatch \
  --sacct  examples/oom/sacct.csv \
  --stderr examples/oom/slurm-1001.err
# -> examples/oom/job.doctor.sbatch with #SBATCH --mem=24G
```

## Machine-readable output

```bash
slurm-doctor analyze --sacct examples/timeout/sacct.csv --format json
slurm-doctor analyze --sacct examples/timeout/sacct.csv --format markdown
```

These examples double as integration tests; see `tests/test_pipeline.py`.
