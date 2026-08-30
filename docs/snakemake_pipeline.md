# Snakemake Pipeline Specification

Documents the DAG contract used for local and HPC execution. The pipeline is
parameterised by a single `trace_name` (`physical_job` or `deeplearn_job`) and
driven by a config file (`config.yaml` for production, `config.smoke.yaml` for
smoke tests). All scripts are invoked as modules: `python -m src.<name>`.

## 1. Goal

Reproducible end-to-end workflow from a raw trace to statistical outputs and
figures, with per-run reproducibility metadata (git commit, seed, split id).

## 2. Rule graph

```
make_split
   └─> train_agent (per seed × algo)
          └─> eval_run (per seed × algo)
                 └─> aggregate
                        └─> stats
                              └─> select_best ─┬─> holdout_eval ─> holdout_aggregate ─┐
                                               └─> visualise ──────────────────────────┤
   baseline + random ─> baseline_aggregate ─> baseline_compare ─────────────────────────┤
   baseline_holdout + random ─> baseline_holdout_aggregate ─────────────────────────────┘
```

`holdout_eval` runs all six DRL treatments across the configured seeds on the
reserved holdout split for final reporting. The holdout remains excluded from
training, tuning, and selection. `rule all` requires `visualise`,
`baseline_compare`, `holdout_aggregate`, and `baseline_holdout_aggregate`.

`train_agent` and `eval_run` fan out over the cross product of `seeds` ×
`algorithms` (production: 10 × 6 = 60 of each). The baseline branch
(`run_baseline`) is independent of the DRL branch and only needs the split.

## 3. Rule contracts

| Rule | Script | Key inputs | Key outputs |
|------|--------|-----------|-------------|
| `make_split` | `src.make_split` | `data/<trace>.csv` | `data/splits/<trace>_dev70.tsv`, `<trace>_holdout30.tsv`, `data/splits/logs/<trace>_r70.json` |
| `train_agent` | `src.train_agents` | dev split | `trained_model/<trace>/<seed>/<algo>/selector/<step>.zip` (+ `.train_complete` marker), manifest row in `logs/run_log.csv` |
| `eval_run` | `src.evaluate_agents` | trained model (via manifest) | `result/<trace>/eval_runs/runs/*.csv` (+ per-run complete marker) |
| `aggregate` | `src.aggregate_results` | eval run CSVs | `result/<trace>/aggregate/{eval_wide,seed_summary,algorithm_summary}.csv`, `aggregate_metadata.json` |
| `stats` | `src.statistical_test` | `seed_summary.csv` | `result/<trace>/stats/{stats_summary.json,pairwise_nemenyi.csv,confidence_intervals.csv,page_trend.csv,cd_diagram_input.csv,stats_meta.json}` |
| `select_best` | `src.select_best` | stats + aggregate | `result/<trace>/best/best_algorithm.json` |
| `holdout_eval` | `src.evaluate_agents` | all trained treatments + holdout split | `result/<trace>/holdout/runs/*.csv` (all six treatments × configured seeds, via `--eval-trace`) |
| `holdout_aggregate` | `src.aggregate_results` | holdout runs | `result/<trace>/holdout/holdout_summary.csv` |
| `baseline` / `baseline_random` | `src.run_baseline` / `src.random_control` | dev split | deterministic heuristic rows plus seeded random-control rows under `result/<trace>/baseline/` |
| `baseline_aggregate` | `src.baseline_aggregate` | heuristic/random completion markers + rows | `result/<trace>/baseline/{baseline_summary,baseline_eval_wide}.csv` |
| `baseline_compare` | `src.baseline_compare` | best + summaries | deterministic one-sample tests and descriptive table under `result/<trace>/baseline/` |
| `baseline_holdout*` | same control scripts | holdout split | `result/<trace>/baseline_holdout/baseline_summary.csv` |
| `visualise` | `src.visualise` | best + stats + aggregate | plots under `plots/`, `.visualise_complete` marker |

## 4. Config

Workflow parameters live in `config.yaml` (production) / `config.smoke.yaml`
(smoke). Key keys: `trace_name`, `seeds`, `algorithms`, `trad_algorithms`,
`allocators`, `save_interval`, `total_saving` (total steps = `save_interval ×
total_saving`), `window_size`, `tail_size`, `buffer_size`, `n_envs`,
`batch_size`, `n_epochs`, `learning_rate`, `alpha`, `eval_deterministic`,
`eval_max_steps`, `allow_partial_evaluation` (smoke only), `pareto_metrics`,
`pareto_tiebreakers`, `visualisation`.

SLURM runner settings (executor, jobs, container, resources) live **only** in
`profiles/slurm/config.yaml` — the config files carry no runner keys.

## 5. Profiles

- SLURM profile: `profiles/slurm/config.yaml` (executor plugin, `--use-singularity`
  with `apptainer-args: "--nv --bind /scratch"`, default resources).
- Submit: `snakemake --configfile config.yaml --profile profiles/slurm`
  (or `just run_full_slurm`).

## 6. Failure and resume

- `rerun-incomplete: true` in the profile re-runs jobs whose outputs are
  incomplete after a crash.
- Snakemake skips rules whose outputs are up to date; `.train_complete` /
  `.*_complete` marker files make expensive stages idempotent.
- Training writes a checkpoint every `save_interval` steps, so a killed
  `train_agent` job resumes from the last checkpoint rather than from scratch.

## 7. Validation checklist

- [ ] `just dry_run_smoke` — smoke DAG resolves
- [ ] `just run_smoke` (local) or `just run_smoke_slurm` (cluster) finishes
- [ ] `just dry_run` — production DAG resolves
- [ ] run metadata has a non-null `git_commit`

## 8. Example commands

```bash
just dry_run_smoke                                   # validate smoke DAG
just run_smoke                                       # local smoke run
snakemake --configfile config.yaml --profile profiles/slurm   # full run on cluster
just run_full_slurm deeplearn                        # full run, GPU trace
```
