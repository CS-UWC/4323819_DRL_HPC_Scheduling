# Methodology Protocol (Template)

Use this file as the canonical methodology specification for Submission 2.

## 1. Study Scope

- Thesis title:
- Submission milestone:
- Date updated:
- Author:

## 2. Research Questions and Hypotheses

### Research Questions

- RQ1:
- RQ2:
- RQ3:

### Hypotheses

- H1:
- H2:
- H3:
- H4:

## 3. Algorithm Set

| Algorithm | Family | Masking | Implementation package | Notes |
|---|---|---|---|---|
| MaskablePPO | Policy gradient | Yes | sb3-contrib | |
| MaskableA2C | Actor-critic | Yes | local (`github_repos/herasched/src/`) | custom implementation |
| MaskableDQN | Value-based | Yes | local (`github_repos/herasched/src/`) | custom implementation |
| PPO | Policy gradient | No | stable-baselines3 | |
| A2C | Actor-critic | No | stable-baselines3 | |
| DQN | Value-based | No | stable-baselines3 | |

## 4. Environment and Data

- Environment implementation path:
- Primary traces:
- Topologies:
- Allocator policy:

### Data Governance

- Development/train split definition: first 70% of trace rows after stable time sort on `Submit` (`*_dev70.tsv`)
- Final holdout definition: last 30% of trace rows after stable time sort on `Submit` (`*_holdout30.tsv`)
- Optional blocked CV configuration: allowed on development/train partition only
- Leakage prevention controls: script-level holdout guard in `train_agents.py` rejects holdout-like trace paths

## 5. Training Protocol

- Timesteps per run: smoke default `--save_interval 1000 --total_saving 1` (1k steps)
- Seed set: fixed seed for smoke reproducibility (for example `123456`), multi-seed set for full comparison runs
- Hyperparameter source:
- Checkpoint cadence: every `save_interval` steps to `trained_model/<name>/selector/`
- Logging path conventions:

### Command Template

```bash
python train_agents.py --algo <algo> --trace splits/<trace>_dev70.tsv --seed <seed> --save_interval <n> --total_saving <k>
```

Note for DQN smoke on high-dimensional dict observations:

- use reduced replay buffer to avoid memory exhaustion, e.g. `--buffer-size 2000`.

## 6. Evaluation Protocol

- Deterministic/stochastic policy mode:
- Evaluation trace/split:
- Evaluation outputs:
- Resource profiling method:

### Command Template

```bash
python evaluate_agents.py --models-dir <dir> --split <split_id> --output <dir>
```

## 7. Metrics

### Primary Metrics

- average waiting time
- average slowdown

### Secondary Metrics

- max waiting time
- max slowdown
- average turnaround
- CPU utilization
- node utilization

### Resource Metrics

- training wall-clock
- inference decision latency
- peak memory footprint

## 8. Statistical Workflow

Sequence:

1. Shapiro-Wilk
2. Friedman
3. Nemenyi
4. epsilon2 effect size
5. bootstrap 95% CI
6. CD diagram inputs
7. Pareto analysis

### Command Template

```bash
python statistical_tests.py --input <aggregate_csv> --output <analysis_dir>
```

## 9. Output Contracts

- Training outputs:
- Evaluation metrics files:
- Aggregated summary tables:
- Statistical results files:
- Plot outputs:

## 10. Threats to Validity

- Internal validity:
- External validity:
- Construct validity:
- Mitigation actions:

## 11. Reproducibility Metadata

- Git commit hash:
- Nix environment version:
- Seeds used:
- Split ID:
- Command logs location:
