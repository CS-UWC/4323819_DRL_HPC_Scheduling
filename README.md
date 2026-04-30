# HPC-DRL-Scheduler (Consolidation Repository)

This repository is the target clean structure for final project packaging.

Current active implementation still occurs in `github_repos/herasched/` in the main workspace.

## Purpose

- host a clean, public-facing project structure;
- collect finalized training/evaluation/statistics workflow components;
- support migration to a future GitHub Wiki-based documentation flow.

## Current Status

- consolidation repo structure exists;
- docs scaffolding is in progress under `docs/`;
- operational source of truth remains root `AGENTS.md` in the parent workspace;
- implementation source of truth remains `github_repos/herasched/` until migration checkpoint.

## Planned Consolidation Scope

This repo will eventually contain:

- training entry points and configs;
- evaluation and aggregation scripts;
- statistical analysis scripts and outputs;
- reproducibility documentation and runbooks;
- milestone-aligned presentation summaries and public references.

## Interim Documentation Pack

See `docs/` for templates used to track:

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
├── docs/
├── training/
├── evaluation/
├── statistical_analysis/
├── data/
├── presentations/
└── tests/
```

## Migration Rule

Do not migrate partially defined workflow code.

Promote components into this repo only when they satisfy:

- stable CLI and output contracts;
- smoke-tested locally;
- aligned with data governance and reproducibility rules;
- documented in `docs/`.
