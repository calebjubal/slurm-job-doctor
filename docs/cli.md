# CLI reference

Installed as `slurm-doctor` (also runnable via `python -m slurm_job_doctor.cli`).

## `analyze`

Diagnose a completed job and print recommendations.

```bash
# From a live cluster (runs sacct for you)
slurm-doctor analyze --job-id 123456

# From local files (no Slurm needed)
slurm-doctor analyze \
  --sbatch examples/oom/job.sbatch \
  --sacct  examples/oom/sacct.csv \
  --stdout examples/oom/slurm-1001.out \
  --stderr examples/oom/slurm-1001.err
```

Options:

| Option | Meaning |
| --- | --- |
| `--job-id` | Completed job id; collected via `sacct`. |
| `--sbatch` | Path to the batch script. |
| `--sacct` | Path to an `sacct` dump (`--parsable2` or CSV). |
| `--stdout` / `--stderr` | Paths to job log files. |
| `--config` | Path to a `.doctor.yml` site config. |
| `--format` | `terminal` (default), `json`, or `markdown`. |
| `--patch` | Also write `<name>.doctor.sbatch`. |

At least one of `--job-id / --sbatch / --sacct / --stdout / --stderr` is required.

## `patch`

Generate a corrected script from a diagnosis.

```bash
# Write job.doctor.sbatch next to the original
slurm-doctor patch --sbatch job.sbatch --job-id 123456

# Overwrite in place (backs up to job.sbatch.bak first)
slurm-doctor patch --sbatch job.sbatch --job-id 123456 --apply
```

`--output/-o` sets an explicit destination; `--apply` overwrites the original after
creating a `.bak`. The patcher never lowers memory after an OOM (or walltime after a
timeout) — those edits are dropped by the safety layer.

## `version`

Print the installed version.

## Planned commands

`monitor` (v0.2.0), `collect` (v0.3.0), `train` (v0.4.0), and `dashboard` (v0.5.0) are
registered but currently print a roadmap notice. See [roadmap.md](roadmap.md).
