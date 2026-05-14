# DRL HPC Scheduling

Imperative Analysis through Reproducible Pipelines

This repository provides an end-to-end, reproducible pipeline to train, evaluate, aggregate, and statistically compare deep reinforcement learning (DRL) schedulers for heterogeneous HPC workloads. The workflow targets six DRL algorithms across three families (PPO, A2C, DQN) and their maskable variants, with time-aware data splits and a non-parametric statistical analysis suite.

The implementation is Nix-first. For cluster execution, the same environment is intended to be containerized with Apptainer (see `docs/workflow_hpc.md`).

## Highlights

- single repo for training, evaluation, aggregation, and statistics
- time-aware split policy with holdout guardrails
- Snakemake orchestration with smoke and full runs
- reproducibility via Nix (pins Python + dependencies)
- structured outputs with metadata sidecars for audit trails

## Quickstart (Nix)

```bash
cd Project_Github
nix develop
just dry_run_smoke
```

## Key Commands

Snakemake targets (via just):

```bash
just dry_run_smoke
just run_smoke
just run_full
just run_full TRACE=deep_learn
```

Direct script entrypoints:

```bash
python src/make_split.py --src physical_job
python src/train_agents.py --algo maskable_a2c --trace splits/physical_job_dev70.tsv --seed 123456 --save_interval 1000 --total_saving 1
python src/evaluate_agents.py --manifest logs/run_log.csv --output-dir result/physical_job/eval_runs
python src/aggregate_results.py --manifest logs/run_log.csv --eval-root result/physical_job/eval_runs/runs --output-dir result/physical_job/aggregate
python src/statistical_test.py --input result/physical_job/aggregate/seed_summary.csv --output-dir result/physical_job/stats
```

## Project Layout

```
Project_Github/
├── src/                 # pipeline scripts + HPCsim + custom maskable algorithms
├── docs/                # methodology, workflow, and reproducibility docs
├── data/                # traces, topologies, splits (not committed)
└── presentations/       # presentation artefacts
```

## Results (Coming Soon)

- primary metrics summary table (avg_waiting, avg_slowdown)
- secondary metrics table (turnaround, utilization)
- CD diagram inputs and plots
- seed-level summary and statistical outputs

When results land, this section will link to the generated artefacts and the evidence map in `docs/submission2_evidence_map.md`.

## Key Resources (Citations Pending)

- HPCSim environment (Wang et al.)
- stable-baselines3 (PPO, A2C, DQN)
- sb3-contrib (MaskablePPO)

## Documentation Index

- `docs/methodology_protocol.md`
- `docs/data_split_policy.md`
- `docs/workflow_local.md`
- `docs/workflow_hpc.md`
- `docs/snakemake_pipeline.md`
- `docs/reproducibility_checklist.md`

## Contact

Justin M. Cheney — 4323819@myuwc.ac.za
