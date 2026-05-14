# HPC-DRL-Scheduler (Consolidation Repository)

This repository is the consolidated structure for final project packaging and public release.

Active implementation now lives in this repository under `src/`.

## Purpose

- host a clean, public-facing project structure;
- collect finalized training/evaluation/statistics workflow components;
- provide a stable entry point for documentation and artefacts;
- support migration to a future GitHub Wiki-based documentation flow.

## Current Status

- consolidated pipeline code lives under `src/`;
- docs scaffolding is in progress under `docs/`;
- operational source of truth remains root `AGENTS.md` in the parent workspace.

## Planned Consolidation Scope

This repo will eventually contain:

- training entry points and configs;
- evaluation and aggregation scripts;
- statistical analysis scripts and outputs;
- reproducibility documentation and runbooks;
- migration-ready Snakemake workflow and profiles;
- milestone-aligned presentation summaries and public references.

## Documentation Pack

See `docs/` for living documents that track:

- methodology protocol;
- split and leakage policy;
- local workflow;
- HPC workflow;
- Snakemake pipeline;
- reproducibility checklist;
- Submission 2 evidence mapping.

## Structure

```
Project_Github/
├── src/
├── docs/
├── data/
└── presentations/
```

## Migration Rule

Do not migrate partially defined workflow code.

Promote components into this repo only when they satisfy:

- stable CLI and output contracts;
- smoke-tested locally;
- aligned with data governance and reproducibility rules;
- documented in `docs/`.

## Next Migration Milestone

- document Apptainer/Nix container strategy in `docs/workflow_hpc.md`;
- add Snakemake Slurm profile and cluster submission notes;
- export the DAG figure and reference it in `docs/methodology_protocol.md`;
- keep root limited to `README.md`, `Snakefile`, `justfile`, `flake.nix` (plus future Apptainer/Slurm assets);
- move any custom Nix code into a `nix/` directory (referenced from `flake.nix`).
