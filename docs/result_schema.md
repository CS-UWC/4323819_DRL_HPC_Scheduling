# Result and Manifest Contracts

This file defines the stable interfaces between pipeline stages. Column constants in `src/utils.py` and rule outputs in `Snakefile` are executable authorities.

## Training manifest

Path: `logs/run_log.csv`

Required columns:

```text
run_id, treatment_id, algorithm, use_masking, seed, window_size, tail_size,
split_id, model_path, trace_file, topology_file, node_file
```

A row is uniquely identified by `(split_id, treatment_id, seed)`. Rewriting the same logical run with identical identity is idempotent; conflicting metadata is rejected. Checkpoints use `trained_model/<trace>/<seed>/<algorithm>/selector/<step>.zip`; the manifest path, rather than directory discovery, is the evaluation interface.

## Evaluation run

Development path: `result/<trace>/eval_runs/runs/<run_id>_metrics.csv`

Holdout path: `result/<trace>/holdout/runs/<run_id>_metrics.csv`

Required identity/completion fields:

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

Resource fields include `decision_latency_mean_ms` and `eval_wall_s`. Core numeric metrics must be finite. Production aggregation rejects rows where `evaluation_complete` is false; smoke aggregation requires the explicit `--allow-partial` interface.

## Aggregate outputs

Directory: `result/<trace>/aggregate/`

| File | Grain | Contract |
|---|---|---|
| `eval_wide.csv` | one canonical evaluation run | normalized run, treatment, seed, split, completion, metric, and timing fields |
| `seed_summary.csv` | one treatment × seed × split | identity columns plus metric means/std/counts as available |
| `algorithm_summary.csv` | one treatment × split | metric means/std/counts across seeds |
| `aggregate_metadata.json` | one aggregation | source paths, commit, command, row counts, partial-evaluation policy, timestamp |

Required seed-summary identity columns are `split_id`, `seed`, `algorithm`, `use_masking`, and `treatment_id`.

## Statistics and selection

Directory: `result/<trace>/stats/`

```text
stats_summary.json
pairwise_nemenyi.csv
confidence_intervals.csv
confidence_curves.csv
page_trend.csv
cd_diagram_input.csv
stats_meta.json
```

Selection writes `result/<trace>/best/best_algorithm.json`, containing at least the selected `treatment_id`, configured Pareto metrics/tie-breakers, candidate rationale, and source references.

## Holdout

Holdout evaluation uses the same per-run schema but a different evaluation trace. It preserves the development model's split identity and writes all-six treatment seed/treatment summaries under `result/<trace>/holdout/`. Holdout files must never be inputs to training or `select_best`.

## Controls

Heuristic and random-control rows use distinct treatment identities. Deterministic heuristic IDs encode masking/backfill state, for example `sjf__mask_false__nobf`; masked random control is `random__mask_true`. Baseline summaries and comparisons are under `result/<trace>/baseline/` and holdout counterparts under `result/<trace>/baseline_holdout/`.

## Curated release

`results/v1/manifest.json` declares every published file. `scripts/validate_results_release.py` requires:

- exact declared/file inventory agreement;
- matching byte size and SHA-256;
- matching generation-script hash where declared;
- six treatments × ten seeds for each development/holdout trace summary;
- consistent algorithm, masking, and split identity fields.

Run:

```bash
python scripts/validate_results_release.py
```
