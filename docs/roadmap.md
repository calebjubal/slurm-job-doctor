# Roadmap

This document lays out the **planned** development sequencing for `slurm-job-doctor`.
It is a forward-looking plan, not a changelog — it describes the order in which the
phases are intended to be built and which release each phase lands in. Actual release
dates are recorded in git tags and `CHANGELOG.md`.

The work is organized into twelve milestones (M1–M12). Each milestone is a self-contained
chunk of value that can be built, tested, and released on its own. Milestones map onto the
phases described in the `README.md` implementation plan.

## Milestone plan

| Milestone | Phase(s)            | Deliverable                                        | Target release |
|-----------|---------------------|----------------------------------------------------|----------------|
| M1        | Phase 0             | Repo scaffold, packaging, CI-ready layout          | pre-0.1        |
| M2        | Phase 1             | Unit/time parser (`16G`, `02:00:00`, `1-02:00:00`) | 0.1.0          |
| M3        | Phase 2             | `sbatch` parser (directives + body preservation)   | 0.1.0          |
| M4        | Phase 3             | `sacct` parser → `JobRecord`                        | 0.1.0          |
| M5        | Phase 4             | Log parser (oom / cuda / timeout / import)          | 0.1.0          |
| M6        | Phase 5             | Diagnosis engine (oom, timeout, cpu, mem, gpu, env) | 0.1.0          |
| M7        | Phase 6             | Recommendation engine + queue-impact estimator     | 0.1.0          |
| M8        | Phase 7             | `sbatch` patcher (`.doctor.sbatch`, safe backups)   | 0.1.0          |
| M9        | Phase 8–9           | Terminal / JSON / Markdown reports + CLI + examples | 0.1.0          |
| M10       | (hardening)         | Dogfood on example jobs, fix real bugs              | 0.1.x          |
| M11       | v0.2 work           | Live job monitor (`sstat`)                          | 0.2.0          |
| M12       | Phase 10+ (future)  | Historical collection, ML right-sizing, dashboard   | 0.3.0+         |

## Versioning policy

- **Minor** releases (`0.1`, `0.2`, …) add a capability area: rule-based doctor, live
  monitor, historical analysis, ML, dashboard.
- **Patch** releases (`0.1.1`, `0.1.2`, …) are bug fixes and hardening found while
  dogfooding a minor release. Each patch tag corresponds to a real, described fix in
  `CHANGELOG.md` — never a cosmetic bump.

## Release targets

### 0.1.0 — Rule-Based Doctor (M2–M9)
The first usable release. Parses local `sbatch` / `sacct` / log files, diagnoses OOM,
timeout, and CPU/memory inefficiency, recommends fixes, and emits a patched
`.doctor.sbatch`. No Slurm install required for the file-based workflow.

### 0.1.x — Hardening (M10)
Fixes for issues found by running the CLI end-to-end against the bundled example jobs.

### 0.2.0 — Live Job Monitor (M11)
Adds `sstat`-based monitoring of running jobs with memory / walltime / CPU risk
warnings.

### 0.3.0+ — Future (M12)
Historical job collection, a local accounting database, ML-based right-sizing, and a
Streamlit dashboard. Deliberately deferred until the rule-based core is solid (see the
safety principle: the tool should never pretend to know more than the cluster).
