# Methodology Protocol

Status: frozen protocol for the v1 evidence release

Study: *Deep Reinforcement Learning for HPC Job Scheduling: A Statistical Evaluation*

Owner: Justin M. Cheney

Last updated: 2026-08-30

## Research objective

Identify low-resource DRL scheduling treatments that retain at least 90% of the best observed schedule quality on heterogeneous HPC workloads, while testing whether algorithm family or action masking produces repeatable differences.

Research questions:

1. Do PPO, A2C, and DQN families differ on waiting and slowdown metrics?
2. Does action masking improve schedule quality, or chiefly enforce feasible decisions?
3. Do development conclusions persist on an isolated time-ordered holdout and against heuristic/random controls?

The analysis uses two-sided non-parametric repeated-measures tests at `alpha=0.05`. Absence of statistical significance is not treated as evidence of equivalence; the paper's equivalence tables use separately declared practical margins.

## Treatments and controls

| Treatment | Family | Masking | Implementation |
|---|---|---:|---|
| PPO | policy gradient | no | stable-baselines3 |
| A2C | actor-critic | no | stable-baselines3 |
| DQN | value-based | no | stable-baselines3 |
| MaskablePPO | policy gradient | yes | sb3-contrib |
| MaskableA2C | actor-critic | yes | local `src/a2c_mask.py` |
| MaskableDQN | value-based | yes | local `src/dqn_mask.py` |

Controls are LCFS, SJF, and UNICEP plus a seed-paired masked uniform-random policy. The primary heuristic comparison disables backfill to match the mechanism available to the DRL policies. Backfill-enabled controls form a sensitivity band only; treatment IDs distinguish `bf` from `nobf`.

## Environment and workloads

HPCSim is a trace-driven Gymnasium environment using a best-fit allocator. The selector observes the queue/cluster state and chooses a job; maskable treatments cannot choose infeasible actions.

| Trace | Source rows | Topology |
|---|---:|---|
| `physical_job` | 84,135 | `physical_topology.txt` |
| `deeplearn_job` | 68,720 | `deeplearn_topology.txt` |

Exact input formats are defined in [`HPCSim.md`](HPCSim.md). The Snakefile derives topology from `trace_name`.

## Data governance

Each trace is stable-sorted by `Submit`. The earliest 70% is development; the latest 30% is holdout. There is no random shuffle. Training, statistical comparison, and selection use development only. All six frozen treatments are evaluated on holdout for final reporting; holdout does not feed tuning or selection. See [`data_split_policy.md`](data_split_policy.md).

## Training protocol

Production configuration is six treatments × ten fixed seeds per trace. Each run uses 3M timesteps (`save_interval=300000`, `total_saving=10`), `n_envs=20`, `window_size=512`, `tail_size=64`, batch size 2048, five optimization epochs, and linear learning-rate decay from `3e-4`. `config.yaml` is the hyperparameter authority.

```bash
python -m src.train_agents \
  --algorithm <algorithm> --name <run-name> --trace data/splits/<trace>_dev70.tsv \
  --seed <seed> --save_interval 300000 --total_saving 10
```

Training records the treatment, masking mode, seed, split ID, model path, input paths, Git commit, command, and timestamps through manifest and metadata sidecars.

## Evaluation and selection

Development and holdout policy evaluation is deterministic (`eval_deterministic: true`). Production evaluation is uncapped and partial rows are rejected. Smoke evaluation is explicitly capped and may be aggregated only because `config.smoke.yaml` sets `allow_partial_evaluation: true`.

Per-run outputs record completion state, termination reason, requested cap, decisions, completed jobs, scheduling metrics, wall time, and decision latency. Development seed summaries feed Pareto selection using configured metrics and confidence-interval tie-breakers. Nemenyi results remain reported evidence, not an elimination rule.

All six treatments then run on holdout across all ten seeds. This is final reporting, not a second selection pass.

## Metrics

Primary, lower is better:

- average waiting time;
- average slowdown.

Secondary:

- maximum waiting time (lower);
- maximum slowdown (lower);
- average turnaround time (lower);
- CPU utilization (higher);
- GPU utilization where applicable (higher).

Resource evidence:

- training wall-clock;
- evaluation wall-clock;
- inference decision latency;
- recorded memory footprint where available.

## Statistical workflow

For each metric, paired seed observations are analyzed by:

1. Shapiro-Wilk as a report-only distribution diagnostic;
2. Friedman omnibus test;
3. Kendall's W effect size;
4. Nemenyi post-hoc when the omnibus test is significant;
5. paired Wilcoxon-based confidence intervals;
6. Page trend test for ordered behavior;
7. critical-difference inputs for rank visualization;
8. configured Pareto and CI tie-breaking on development.

Deterministic heuristic comparisons use one-sample Wilcoxon tests against the fixed heuristic value. The stochastic random control is retained descriptively and compared through its seed-paired evidence rather than treated as a deterministic constant.

```bash
python -m src.statistical_test \
  --input result/<trace>/aggregate/seed_summary.csv \
  --output-dir result/<trace>/stats --alpha 0.05
```

## Output contracts

The machine-readable schemas and directory contracts are defined in [`result_schema.md`](result_schema.md). The curated v1 publication includes only aggregate seed/treatment summaries, statistical tables, selection rationale, and paper-facing evidence. Raw runs, models, logs, and generated splits are excluded.

## Threats to validity

- **Internal:** historical unmasked paper rows were capped, and two physical source evaluations duplicate scheduling metrics with different timing. Both are disclosed in `results/v1/`.
- **External:** two traces from one upstream environment do not establish cross-centre generality.
- **Statistical:** ten seeds limit power for small effects and make rank conclusions sensitive to variance.
- **Construct:** waiting/slowdown and utilization do not capture every operational objective, including fairness, energy, and failures.
- **Implementation:** locally implemented maskable A2C/DQN may differ from other libraries despite shared interfaces.

## Reproducibility record

The frozen release records source commit `fae1c739dd8e1743cd61d9cf909b23fa6e7d32a1`; the public result-bundle base is `fa0e299b58fa5ce297bb52a439d82658330600df`. Seeds, split IDs, source hashes, commands, artifact hashes, and provenance caveats are in [`../results/v1/manifest.json`](../results/v1/manifest.json). Validate with `python scripts/validate_results_release.py`.
