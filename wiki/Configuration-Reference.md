# Configuration Reference

Use these files as the authorities:

- [`config.yaml`](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/config.yaml): production experiment;
- [`config.smoke.yaml`](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/config.smoke.yaml): integration smoke run;
- [`Snakefile`](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/Snakefile): rule wiring and topology mapping;
- [`profiles/slurm/config.yaml`](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/profiles/slurm/config.yaml): cluster execution.

| Group | Important keys |
|---|---|
| Workload | `trace_name`, `node_file` |
| Matrix | `seeds`, `algorithms`, `trad_algorithms`, `random_control` |
| Training | `save_interval`, `total_saving`, `n_envs`, `batch_size`, `n_epochs`, `learning_rate`, `buffer_size` |
| Observation | `window_size`, `tail_size` |
| Evaluation | `eval_deterministic`, `eval_max_steps`, `allow_partial_evaluation` |
| Controls | `baseline_backfill`, `baseline_only` |
| Selection | `pareto_metrics`, `pareto_tiebreakers`, `alpha` |

The Snakefile derives topology from `trace_name`: physical uses `physical_topology.txt`; deeplearn uses `deeplearn_topology.txt`. Allocation is fixed to `best_fit`, and the workflow always generates its supported result plots; neither behavior has a speculative config switch.

## Smoke versus production

| | Smoke | Production |
|---|---:|---:|
| Seeds | 2 | 10 |
| DRL treatments | 2 | 6 |
| Steps per run | 200 | 3,000,000 |
| Evaluation | capped at 5 decisions | complete |
| Partial aggregation | explicitly allowed | rejected |

## Commands

```bash
just help
just dry_run_smoke physical
just dry_run physical

# Direct equivalents
snakemake --configfile config.smoke.yaml --config trace_name=physical_job --dry-run
snakemake --configfile config.yaml --config trace_name=physical_job --dry-run
```

`just` normalizes positional `physical`/`deeplearn` arguments to `<name>_job`.

For every changed experiment, retain the commit, seeds, split ID, hyperparameter source, exact command, UTC timestamp, and output paths. Do not edit published `results/v1/`; create a new versioned release.
