# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Repo scaffold: packaging (`pyproject.toml`), license, `.gitignore`, `Makefile`,
  `src/` layout, and the development roadmap.
- `parsers.unit_parser`: normalize Slurm memory (`16G` → 16384 MiB) and time
  (`1-02:00:00` → 93600 s) strings, plus formatters for writing them back.
- `models.SbatchScript` + `parsers.sbatch_parser`: extract `#SBATCH` directives
  (long and short forms) while preserving comments, blank lines, body, and order;
  derive GPU count from `--gres`/`--gpus`.
