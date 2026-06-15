# slurm-job-doctor

**slurm-job-doctor** is a Python-based CLI tool for diagnosing failed or inefficient Slurm jobs, recommending better resource requests, and generating patched `sbatch` scripts.

Most HPC users waste time guessing values for:

```bash
#SBATCH --time
#SBATCH --mem
#SBATCH --cpus-per-task
#SBATCH --ntasks
#SBATCH --nodes
#SBATCH --gres=gpu
```

Wrong values lead to:

* `OUT_OF_MEMORY` failures
* walltime kills
* poor CPU efficiency
* wasted GPU allocation
* longer queue wait times
* repeated trial-and-error submissions

`slurm-job-doctor` acts like a local debugging assistant for HPC jobs.

It reads Slurm accounting output, job logs, stderr/stdout files, and batch scripts, then produces a clear diagnosis and a safer corrected script.

---

## Project Goal

The goal is not to replace Slurm.

The goal is to help users answer:

```text
Why did my job fail?
Did I request too much memory?
Did I request too many CPUs?
Did I hit walltime?
Was my GPU actually used?
What should I change before resubmitting?
```

---

## Core Features

### 1. Failed Job Diagnosis

Detect common failure patterns:

* Out of memory
* Walltime exceeded
* Node failure
* Cancelled jobs
* GPU/CUDA out-of-memory
* Missing module
* Conda environment not found
* Python import errors
* Incorrect partition
* Invalid account
* Poor CPU utilization
* Poor memory utilization
* GPU requested but not used
* CPU/GPU mismatch
* OpenMP thread mismatch

Example:

```text
Diagnosis:
- Job failed due to OUT_OF_MEMORY.
- Requested memory: 16 GB
- Observed max RSS: 15.7 GB
- stderr contains cgroup memory kill pattern.
- Recommendation: request 24 GB memory and add memory logging.
```

---

### 2. Slurm Accounting Parser

Parses `sacct` output such as:

```bash
sacct \
  --jobs 123456 \
  --format=JobID,JobName,State,ExitCode,Elapsed,Timelimit,ReqMem,MaxRSS,AllocCPUS,NTasks,NodeList \
  --parsable2
```

The parser normalizes:

* job ID
* job name
* state
* exit code
* requested memory
* peak memory
* requested CPUs
* requested tasks
* elapsed time
* walltime limit
* node list
* partition
* account
* user

---

### 3. Running Job Monitor

Uses `sstat` for running job-step metrics.

Example command:

```bash
sstat \
  --jobs 123456.batch \
  --format=JobID,AveCPU,AveRSS,MaxRSS,AveVMSize,MaxVMSize \
  --parsable2
```

This allows live warnings like:

```text
Warning:
- Job has used 92% of requested memory.
- Job is close to walltime limit.
- CPU usage is low compared to allocation.
```

---

### 4. `sbatch` Script Parser

Reads batch scripts and extracts directives:

```bash
#!/bin/bash
#SBATCH --job-name=train_model
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%j.out
#SBATCH --error=logs/%j.err

module load cuda
source activate ml
python train.py
```

Parsed output:

```json
{
  "job_name": "train_model",
  "partition": "gpu",
  "gres": "gpu:1",
  "cpus_per_task": 16,
  "mem": "32G",
  "time": "02:00:00",
  "output": "logs/%j.out",
  "error": "logs/%j.err",
  "commands": [
    "module load cuda",
    "source activate ml",
    "python train.py"
  ]
}
```

---

### 5. Rule-Based Recommendations

The first implementation should use deterministic rules before ML.

Examples:

#### Memory under-requested

```text
If State = OUT_OF_MEMORY:
    recommended_mem = max(MaxRSS * 1.5, requested_mem * 1.25)
```

#### Memory over-requested

```text
If MaxRSS < 40% of requested memory:
    recommended_mem = MaxRSS * 1.3
```

#### Time under-requested

```text
If State = TIMEOUT:
    recommended_time = elapsed_time * 1.5
```

#### CPU over-requested

```text
If CPU efficiency < 30%:
    recommend lowering --cpus-per-task
```

#### OpenMP mismatch

```text
If --cpus-per-task=32
and OMP_NUM_THREADS=1:
    warn user that 31 CPUs may be wasted
```

---

### 6. Script Patcher

Generates a corrected `sbatch` file.

Input:

```bash
hpcdoctor patch train.sbatch --job-id 123456
```

Output:

```bash
#!/bin/bash
#SBATCH --job-name=train_model
#SBATCH --partition=gpu
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=03:00:00
#SBATCH --output=logs/%j.out
#SBATCH --error=logs/%j.err

set -euo pipefail

echo "Job started on $(date)"
echo "Running on node: $(hostname)"
echo "SLURM_JOB_ID=$SLURM_JOB_ID"
echo "SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK"

export OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}

/usr/bin/time -v python train.py

echo "Job finished on $(date)"
```

The patched file is saved as:

```text
train.doctor.sbatch
```

---

### 7. Queue Impact Estimator

The tool should not blindly recommend bigger resources.

Bigger memory and longer walltime may increase queue wait time.

So the tool estimates:

```text
Option A:
  --mem=48G
  --time=03:00:00
  success probability: high
  queue impact: medium

Option B:
  --mem=96G
  --time=08:00:00
  success probability: very high
  queue impact: high
```

Initial implementation can use heuristic scoring.

Later implementation can use historical `sacct` data.

---

### 8. ML-Based Resource Prediction

After the rule-based MVP works, add ML models.

Predicted targets:

* recommended memory
* recommended walltime
* expected failure probability
* expected CPU efficiency
* expected queue impact

Possible models:

* Random Forest
* Gradient Boosting
* XGBoost
* LightGBM
* Quantile Regression

Features:

```text
job_name
partition
requested_memory
max_rss
requested_time
elapsed_time
state
exit_code
alloc_cpus
ntasks
nodes
gpu_count
previous_failures
script_command_hash
user_defined_tags
```

Do not start the project with ML.

Build useful parsing and diagnosis first.

---

## Language and Stack

Primary language:

```text
Python 3.11+
```

Why Python:

* easy CLI development
* strong text parsing
* good data tooling
* good ML ecosystem
* readable for HPC users
* easy installation through `pipx`, `uv`, or `pip`

Core libraries:

```text
typer        - CLI
rich         - terminal UI
pydantic     - typed data models
pandas       - sacct CSV/parsing analysis
scikit-learn - ML predictor later
pytest       - tests
ruff         - linting
mypy         - optional typing check
```

Optional later:

```text
streamlit    - dashboard
plotly       - visual reports
duckdb       - local accounting database
fastapi      - future web API
```

---

## Repository Architecture

```text
slurm-job-doctor/
├── README.md
├── LICENSE
├── pyproject.toml
├── .gitignore
├── .python-version
├── Makefile
├── docs/
│   ├── architecture.md
│   ├── cli.md
│   ├── diagnosis-rules.md
│   ├── examples.md
│   └── roadmap.md
├── examples/
│   ├── oom/
│   │   ├── job.sbatch
│   │   ├── slurm-1001.out
│   │   ├── slurm-1001.err
│   │   └── sacct.csv
│   ├── timeout/
│   │   ├── job.sbatch
│   │   ├── slurm-1002.out
│   │   ├── slurm-1002.err
│   │   └── sacct.csv
│   ├── low_cpu_efficiency/
│   │   ├── job.sbatch
│   │   ├── slurm-1003.out
│   │   ├── slurm-1003.err
│   │   └── sacct.csv
│   └── gpu_not_used/
│       ├── job.sbatch
│       ├── slurm-1004.out
│       ├── slurm-1004.err
│       └── sacct.csv
├── src/
│   └── slurm_job_doctor/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── models/
│       │   ├── __init__.py
│       │   ├── job_record.py
│       │   ├── sbatch_script.py
│       │   ├── diagnosis.py
│       │   ├── recommendation.py
│       │   └── report.py
│       ├── parsers/
│       │   ├── __init__.py
│       │   ├── sacct_parser.py
│       │   ├── sstat_parser.py
│       │   ├── sbatch_parser.py
│       │   ├── log_parser.py
│       │   └── unit_parser.py
│       ├── collectors/
│       │   ├── __init__.py
│       │   ├── command_runner.py
│       │   ├── sacct_collector.py
│       │   ├── sstat_collector.py
│       │   └── file_collector.py
│       ├── diagnosis/
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── oom.py
│       │   ├── timeout.py
│       │   ├── cpu_efficiency.py
│       │   ├── memory_efficiency.py
│       │   ├── gpu.py
│       │   ├── environment.py
│       │   └── patterns.py
│       ├── recommenders/
│       │   ├── __init__.py
│       │   ├── engine.py
│       │   ├── memory.py
│       │   ├── runtime.py
│       │   ├── cpu.py
│       │   ├── gpu.py
│       │   └── queue_impact.py
│       ├── patcher/
│       │   ├── __init__.py
│       │   ├── sbatch_patcher.py
│       │   └── safety.py
│       ├── reporting/
│       │   ├── __init__.py
│       │   ├── terminal.py
│       │   ├── markdown.py
│       │   └── json_report.py
│       ├── ml/
│       │   ├── __init__.py
│       │   ├── dataset_builder.py
│       │   ├── features.py
│       │   ├── train_memory_model.py
│       │   ├── train_runtime_model.py
│       │   └── predict.py
│       └── dashboard/
│           ├── __init__.py
│           └── streamlit_app.py
└── tests/
    ├── test_sacct_parser.py
    ├── test_sstat_parser.py
    ├── test_sbatch_parser.py
    ├── test_unit_parser.py
    ├── test_oom_diagnosis.py
    ├── test_timeout_diagnosis.py
    ├── test_recommenders.py
    └── test_sbatch_patcher.py
```

---

## Module Responsibilities

### `cli.py`

Main entrypoint.

Defines commands:

```bash
slurm-doctor analyze
slurm-doctor collect
slurm-doctor patch
slurm-doctor monitor
slurm-doctor train
slurm-doctor dashboard
```

---

### `models/`

Typed data structures.

Example:

```python
class JobRecord:
    job_id: str
    job_name: str | None
    state: str
    exit_code: str | None
    elapsed_seconds: int | None
    timelimit_seconds: int | None
    requested_memory_mb: int | None
    max_rss_mb: int | None
    allocated_cpus: int | None
    ntasks: int | None
    nodes: list[str]
```

These models should be used across the whole codebase so every parser and recommender speaks the same language.

---

### `parsers/`

Converts raw text into structured objects.

Files:

```text
sacct_parser.py   -> parses completed job accounting output
sstat_parser.py   -> parses running job metrics
sbatch_parser.py  -> parses #SBATCH directives
log_parser.py     -> scans stdout/stderr files
unit_parser.py    -> converts 16G, 8000M, 01:30:00 into normalized values
```

---

### `collectors/`

Runs system commands or reads local files.

Examples:

```bash
sacct --jobs 123456 --parsable2
sstat --jobs 123456.batch --parsable2
```

This layer should be isolated so tests can mock command execution.

---

### `diagnosis/`

Contains diagnosis rules.

Example files:

```text
oom.py               -> detects memory failures
timeout.py           -> detects walltime failures
cpu_efficiency.py    -> detects CPU waste
memory_efficiency.py -> detects memory over/under-request
gpu.py               -> detects GPU problems
environment.py       -> detects module/conda/import errors
patterns.py          -> regex patterns for known failures
```

---

### `recommenders/`

Turns diagnosis into action.

Example:

```text
Diagnosis:
- TIMEOUT

Recommendation:
- Increase --time from 02:00:00 to 03:00:00
- Add checkpointing if runtime is unstable
```

---

### `patcher/`

Updates `sbatch` scripts safely.

Responsibilities:

* preserve comments
* preserve original command body
* update existing `#SBATCH` directives
* insert missing directives
* never overwrite original file unless `--apply` is passed
* write patched file to `*.doctor.sbatch`

---

### `reporting/`

Output formats:

```bash
--format terminal
--format json
--format markdown
```

Terminal output uses rich formatting.

JSON output is useful for automation.

Markdown output is useful for GitHub issues, reports, or documentation.

---

### `ml/`

Optional second-stage system.

Builds predictive models from historical job data.

This should come after the MVP.

---

## CLI Commands

### 1. Analyze a completed job from Slurm

```bash
slurm-doctor analyze --job-id 123456
```

Internally:

```text
CLI
 -> sacct_collector
 -> sacct_parser
 -> diagnosis_engine
 -> recommendation_engine
 -> terminal_report
```

---

### 2. Analyze using local files

```bash
slurm-doctor analyze \
  --sbatch examples/oom/job.sbatch \
  --stdout examples/oom/slurm-1001.out \
  --stderr examples/oom/slurm-1001.err \
  --sacct examples/oom/sacct.csv
```

Useful when Slurm is not available locally.

---

### 3. Generate patched script

```bash
slurm-doctor patch \
  --sbatch job.sbatch \
  --job-id 123456
```

Output:

```text
job.doctor.sbatch
```

---

### 4. Apply patch directly

```bash
slurm-doctor patch \
  --sbatch job.sbatch \
  --job-id 123456 \
  --apply
```

Safety rule:

```text
Never overwrite without creating job.sbatch.bak
```

---

### 5. Monitor a running job

```bash
slurm-doctor monitor --job-id 123456
```

Possible output:

```text
Running Job Health:
- Memory usage: 88% of requested memory
- CPU efficiency: low
- Walltime used: 74%
- Risk: medium
```

---

### 6. Build dataset from historical jobs

```bash
slurm-doctor collect \
  --since 2025-01-01 \
  --output data/jobs.csv
```

---

### 7. Train resource prediction model

```bash
slurm-doctor train memory \
  --input data/jobs.csv \
  --output models/memory_model.pkl
```

---

### 8. Run dashboard

```bash
slurm-doctor dashboard
```

---

## Final CLI User Journey

### Step 1: User submits a job

```bash
sbatch train.sbatch
```

Slurm returns:

```text
Submitted batch job 123456
```

---

### Step 2: Job fails

```text
State: OUT_OF_MEMORY
```

---

### Step 3: User runs doctor

```bash
slurm-doctor analyze --job-id 123456 --sbatch train.sbatch
```

---

### Step 4: Tool collects evidence

```text
sacct data
stderr logs
stdout logs
sbatch directives
resource usage
exit code
```

---

### Step 5: Tool produces diagnosis

```text
Primary issue:
- Memory under-requested

Evidence:
- Job state is OUT_OF_MEMORY
- Requested memory was 16 GB
- MaxRSS was close to requested memory
- stderr contains memory kill pattern

Secondary issue:
- CPU efficiency appears low
```

---

### Step 6: Tool recommends fix

```text
Recommended changes:
- --mem=16G -> --mem=24G
- --cpus-per-task=16 -> --cpus-per-task=8
- Add /usr/bin/time -v
- Add OMP_NUM_THREADS=${SLURM_CPUS_PER_TASK:-1}
```

---

### Step 7: User generates patched script

```bash
slurm-doctor patch --job-id 123456 --sbatch train.sbatch
```

---

### Step 8: User resubmits

```bash
sbatch train.doctor.sbatch
```

---

## Example Output

```text
slurm-job-doctor report
=======================

Job ID: 123456
Job Name: train_model
State: OUT_OF_MEMORY
Exit Code: 0:125

Primary Diagnosis:
  The job was killed because it exceeded memory limits.

Evidence:
  Requested Memory: 16 GB
  Max RSS: 15.7 GB
  stderr pattern: "Detected oom-kill event"

Recommendations:
  1. Increase memory to 24 GB.
  2. Keep CPU count at 8 instead of 16.
  3. Add /usr/bin/time -v for better future diagnostics.
  4. If this is a PyTorch job, log batch size and CUDA memory summary.

Patch:
  train.doctor.sbatch created successfully.

Next Command:
  sbatch train.doctor.sbatch
```

---

## Implementation Plan

### Phase 0: Repo Setup

Tasks:

```bash
mkdir slurm-job-doctor
cd slurm-job-doctor
git init
```

Create Python package:

```bash
mkdir -p src/slurm_job_doctor
touch src/slurm_job_doctor/__init__.py
```

Set up:

```text
pyproject.toml
README.md
LICENSE
.gitignore
tests/
examples/
```

---

### Phase 1: Unit and Time Parser

Build `unit_parser.py`.

It should convert:

```text
16G      -> 16384 MB
16000M   -> 16000 MB
1T       -> 1048576 MB
02:00:00 -> 7200 seconds
1-02:00:00 -> 93600 seconds
```

Tests:

```bash
pytest tests/test_unit_parser.py
```

---

### Phase 2: `sbatch` Parser

Build `sbatch_parser.py`.

It should extract:

```text
--job-name
--partition
--account
--nodes
--ntasks
--cpus-per-task
--mem
--mem-per-cpu
--time
--gres
--gpus
--output
--error
```

It should also preserve:

```text
comments
blank lines
body commands
line order
```

---

### Phase 3: `sacct` Parser

Build `sacct_parser.py`.

Expected input:

```text
JobID|JobName|State|ExitCode|Elapsed|Timelimit|ReqMem|MaxRSS|AllocCPUS|NTasks|NodeList
123456|train|OUT_OF_MEMORY|0:125|00:12:31|01:00:00|16Gn|15700M|8|1|node001
```

Expected output:

```python
JobRecord(
    job_id="123456",
    job_name="train",
    state="OUT_OF_MEMORY",
    requested_memory_mb=16384,
    max_rss_mb=15700,
    allocated_cpus=8
)
```

---

### Phase 4: Log Parser

Build `log_parser.py`.

Detect patterns:

```text
oom-kill
Out Of Memory
CUDA out of memory
DUE TO TIME LIMIT
ModuleNotFoundError
ImportError
command not found
No such file or directory
conda: command not found
cannot allocate memory
```

Return structured evidence:

```python
LogEvidence(
    matched_patterns=["cuda_oom"],
    important_lines=[...],
    severity="high"
)
```

---

### Phase 5: Diagnosis Engine

Build `diagnosis/engine.py`.

Input:

```text
JobRecord
SbatchScript
LogEvidence
```

Output:

```text
list[Diagnosis]
```

Each diagnosis has:

```python
Diagnosis(
    code="OUT_OF_MEMORY",
    severity="critical",
    message="Job exceeded memory limit.",
    evidence=[...]
)
```

---

### Phase 6: Recommendation Engine

Build `recommenders/engine.py`.

Input:

```text
diagnoses
job record
sbatch script
```

Output:

```text
list[Recommendation]
```

Example:

```python
Recommendation(
    directive="--mem",
    old_value="16G",
    new_value="24G",
    reason="Job was killed near requested memory limit."
)
```

---

### Phase 7: Script Patcher

Build `patcher/sbatch_patcher.py`.

Requirements:

* modify only `#SBATCH` lines
* preserve script body
* preserve comments
* add missing directives at top
* generate `.doctor.sbatch`
* create backup when applying changes

---

### Phase 8: Terminal Report

Build `reporting/terminal.py`.

Use rich tables:

```text
Diagnosis table
Evidence table
Recommendation table
Patch summary
```

---

### Phase 9: JSON and Markdown Reports

Useful for automation:

```bash
slurm-doctor analyze --job-id 123456 --format json
slurm-doctor analyze --job-id 123456 --format markdown
```

---

### Phase 10: ML Predictor

Only after the rule-based version works.

Build:

```text
dataset_builder.py
features.py
train_memory_model.py
train_runtime_model.py
predict.py
```

The ML model should never silently override rule-based safety recommendations.

It should provide:

```text
suggested range
confidence score
reasoning features
```

---

## Example `pyproject.toml`

```toml
[project]
name = "slurm-job-doctor"
version = "0.1.0"
description = "Diagnose failed Slurm jobs, right-size resources, and generate patched sbatch scripts."
readme = "README.md"
requires-python = ">=3.11"
authors = [
  { name = "Caleb Chandrasekar" }
]
dependencies = [
  "typer>=0.12.0",
  "rich>=13.0.0",
  "pydantic>=2.0.0",
  "pandas>=2.0.0"
]

[project.optional-dependencies]
ml = [
  "scikit-learn>=1.4.0",
  "joblib>=1.3.0"
]
dashboard = [
  "streamlit>=1.35.0",
  "plotly>=5.0.0"
]
dev = [
  "pytest>=8.0.0",
  "ruff>=0.5.0",
  "mypy>=1.8.0"
]

[project.scripts]
slurm-doctor = "slurm_job_doctor.cli:app"

[tool.ruff]
line-length = 100

[tool.pytest.ini_options]
testpaths = ["tests"]
```

---

## Development Setup

Using `uv`:

```bash
uv venv
uv pip install -e ".[dev]"
```

Or using pip:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Run tests:

```bash
pytest
```

Run linter:

```bash
ruff check .
```

Run CLI locally:

```bash
slurm-doctor --help
```

---

## Minimal MVP Checklist

The first release should support:

* parse local `sbatch` file
* parse local `sacct.csv`
* parse stdout/stderr
* detect OOM
* detect timeout
* detect low CPU efficiency
* recommend memory/time/CPU changes
* generate patched `.doctor.sbatch`
* produce terminal report
* include example failed jobs
* include tests

Do not include ML in the first release.

---

## Roadmap

### v0.1.0 — Rule-Based Doctor

* `sacct` parser
* `sbatch` parser
* log parser
* OOM diagnosis
* timeout diagnosis
* CPU/memory efficiency diagnosis
* terminal report
* patched `sbatch` generation

### v0.2.0 — Live Job Monitor

* `sstat` support
* running job warnings
* memory risk warning
* walltime risk warning

### v0.3.0 — Historical Analysis

* collect historical jobs
* local job database
* user-level efficiency report
* job family grouping

### v0.4.0 — ML Right-Sizing

* memory prediction model
* runtime prediction model
* confidence intervals
* explainable recommendations

### v0.5.0 — Dashboard

* Streamlit dashboard
* job history charts
* resource waste charts
* failure trend analysis

### v1.0.0 — Production-Ready CLI

* stable CLI
* JSON output
* markdown output
* plugin system
* cluster policy config
* documentation site

---

## Safety Principles

`slurm-job-doctor` should never pretend it knows more than the cluster.

Rules:

* never auto-submit jobs by default
* never overwrite scripts without backup
* never recommend lower memory after OOM
* never recommend risky walltime reduction without evidence
* always show evidence behind recommendations
* always allow dry-run mode
* support site-specific config

---

## Site-Specific Config

Different HPC clusters have different policies.

Create:

```text
.doctor.yml
```

Example:

```yaml
cluster:
  name: example-hpc
  default_partition: compute

limits:
  max_mem_gb: 512
  max_walltime_hours: 72

policies:
  prefer_mem_per_cpu: false
  allow_gpu_recommendations: true
  min_memory_safety_factor: 1.25
  timeout_safety_factor: 1.5
```

---

## Example Diagnosis Rules

### OOM Rule

```text
If job state contains OUT_OF_MEMORY:
    diagnosis = critical OOM
```

### Timeout Rule

```text
If state contains TIMEOUT:
    diagnosis = critical TIMEOUT
```

### Memory Waste Rule

```text
If max_rss < 0.4 * requested_memory:
    diagnosis = memory over-requested
```

### CPU Waste Rule

```text
If CPU efficiency < 0.3:
    diagnosis = CPU over-requested
```

### GPU Waste Rule

```text
If GPU requested but no CUDA logs and no GPU utilization evidence:
    diagnosis = possible unused GPU allocation
```

---

## Example GitHub Issue Generated by Tool

````markdown
## Slurm Job Doctor Report

Job ID: 123456  
State: OUT_OF_MEMORY  
Script: train.sbatch  

### Diagnosis

The job likely failed because memory was under-requested.

### Evidence

- Requested memory: 16 GB
- Max RSS: 15.7 GB
- stderr contains memory kill pattern

### Recommended Patch

```diff
- #SBATCH --mem=16G
+ #SBATCH --mem=24G
````

### Next Step

Run:

```bash
sbatch train.doctor.sbatch
```

````

---

## Why This Project Matters

HPC users often waste cluster resources because estimating resource needs is difficult.

This project makes Slurm usage more reliable by giving users a practical feedback loop:

```text
submit job
observe failure or inefficiency
diagnose evidence
recommend fix
patch script
resubmit safely
````

That is the full loop `slurm-job-doctor` is designed to automate.

---

## License

MIT License

---

## Author

Caleb Chandrasekar

---

## Status

Planned MVP.

Current focus:

```text
parser -> diagnosis engine -> recommender -> patcher -> CLI report
```
