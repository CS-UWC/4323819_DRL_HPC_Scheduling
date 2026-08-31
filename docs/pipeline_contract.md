# Pipeline and Result Contract

This file is the authority for workflow stage interfaces, output paths, and machine-readable schemas. `Snakefile` and schema constants in `src/utils.py` are the executable definitions.

## Workflow

```text
make_split
  -> train_agent (treatment × seed)
  -> eval_run
  -> aggregate
  -> stats
  -> select_best
  -> holdout_eval (all frozen treatments × seeds)
  -> holdout_aggregate

baseline + random -> baseline_aggregate -> baseline_compare
baseline_holdout + random -> baseline_holdout_aggregate
stats + aggregate + controls -> visualise
```

Holdout is downstream of development-only selection and never feeds training or selection. Production fans out to six treatments × ten seeds per trace. Smoke uses two treatments × two seeds and an explicit evaluation cap.

## Configuration seam

- `config.yaml`: production experiment parameters;
- `config.smoke.yaml`: bounded integration workflow;
- `profiles/slurm/config.yaml`: executor, container, retries, and cluster resources;
- `justfile`: supported human-facing commands.

Live workflow keys include `trace_name`, `seeds`, `algorithms`, `trad_algorithms`, `random_control`, training hyperparameters, evaluation completion policy, `pareto_metrics`, and `pareto_tiebreakers`. The Snakefile derives topology from `trace_name`. Allocation is fixed to best-fit and supported result plots are unconditional.

## Rule outputs

| Rule | Primary output |
|---|---|
| `make_split` | `data/splits/<trace>_{dev70,holdout30}.tsv`; `data/splits/logs/<trace>_r70.json` |
| `train_agent` | `trained_model/<trace>/<seed>/<algorithm>/selector/<step>.zip`; completion marker; manifest row |
| `eval_run` | `result/<trace>/eval_runs/runs/<run_id>_metrics.csv` |
| `aggregate` | `result/<trace>/aggregate/{eval_wide,seed_summary,algorithm_summary}.csv`; metadata JSON |
| `stats` | `result/<trace>/stats/` statistical tables and metadata |
| `select_best` | `result/<trace>/best/best_algorithm.json` |
| `holdout_eval` | `result/<trace>/holdout/runs/*_metrics.csv` |
| `holdout_aggregate` | holdout seed/treatment summaries and `holdout_summary.csv` |
| control rules | `result/<trace>/{baseline,baseline_holdout}/` summaries |
| `visualise` | plots plus `.visualise_complete` |

## Training manifest

Path: `logs/run_log.csv`

Required columns:

```text
run_id, treatment_id, algorithm, use_masking, seed, window_size, tail_size,
split_id, model_path, trace_file, topology_file, node_file
```

`(split_id, treatment_id, seed)` is unique. An identical rerun is idempotent; conflicting metadata is rejected. Evaluation loads the recorded `model_path` rather than discovering checkpoints by directory convention.

## Evaluation row

Development and holdout use the same schema.

Required identity and completion fields:

```text
run_id, treatment_id, algorithm, use_masking, window_size, tail_size, seed,
split_id, episode_reward, decision_count, completed_job_count,
evaluation_complete, requested_max_steps, termination_reason
```

Required scheduling metrics:

```text
max_waiting, avg_waiting, max_slowdown, avg_slowdown, avg_turnaround,
cpu_utilization, gpu_utilization
```

Resource fields include `decision_latency_mean_ms` and `eval_wall_s`. Core numeric fields must be finite. Production aggregation rejects incomplete/capped evaluations; smoke must opt in through `--allow-partial`.

## Aggregate schema

| File | Grain |
|---|---|
| `eval_wide.csv` | one canonical evaluation run |
| `seed_summary.csv` | one treatment × seed × split |
| `algorithm_summary.csv` | one treatment × split |
| `aggregate_metadata.json` | source paths, commit, command, counts, policy, timestamp |

Seed-summary identities are `split_id`, `seed`, `algorithm`, `use_masking`, and `treatment_id`. Metric mean/std/count columns are generated consistently for downstream statistics and plotting.

## Statistics and selection

`result/<trace>/stats/` contains:

```text
stats_summary.json
pairwise_nemenyi.csv
confidence_intervals.csv
confidence_curves.csv
page_trend.csv
cd_diagram_input.csv
stats_meta.json
```

`best_algorithm.json` records the selected treatment, configured Pareto metrics/tie-breakers, candidate rationale, and source references. Holdout files are forbidden as selector inputs.

## Controls

Deterministic heuristic IDs encode masking and backfill, for example `sjf__mask_false__nobf`. Masked random control is `random__mask_true` and retains its seeds. Random is descriptive/seed-paired evidence, not a deterministic one-sample reference.

## Release contract

`results/v1/manifest.json` declares every published artifact. `scripts/validate_results_release.py` enforces:

- declared inventory equals files on disk;
- byte sizes and SHA-256 hashes match;
- generation-script hashes match where declared;
- each development/holdout trace summary has the exact six-treatment × ten-seed grid;
- algorithm, masking, and split identities are consistent.

## Failure, resume, and validation

Completion markers make expensive stages idempotent; the SLURM profile enables `rerun-incomplete` and retries transient failures. Training resumes from its latest checkpoint.

```bash
nix run .#test
just dry_run_smoke physical
just dry_run_smoke deeplearn
just dry_run physical
just dry_run deeplearn
python scripts/validate_results_release.py
```
