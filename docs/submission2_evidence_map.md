# Submission 2 Evidence Map

Status: completed against the v1 public evidence release, 2026-08-30.

| Claim | Paper area | Claim | Versioned source | Published evidence | Status |
|---|---|---|---|---|---|
| C-001 | Methodology | Six DRL treatments cover PPO/A2C/DQN with and without masking | `docs/methodology_protocol.md`; `config.yaml` | `results/v1/manifest.json` experiment matrix | evidenced |
| C-002 | Data | Earliest 70% development and latest 30% holdout are time ordered | `docs/data_split_policy.md`; `src/make_split.py` | split IDs in `results/v1/manifest.json` and seed summaries | evidenced |
| C-003 | Leakage | Holdout cannot feed training or selection | `src/train_agents.py`; `Snakefile`; `docs/data_split_policy.md` | all-six holdout summaries under `results/v1/tables/*/holdout/` | evidenced |
| C-004 | Workflow | Snakemake automates split → train → eval → aggregate → stats → select → holdout | `Snakefile`; `docs/snakemake_pipeline.md` | tested DAG contracts in `tests/test_pipeline_contracts.py` | evidenced |
| C-005 | Evaluation | Six treatments × ten seeds are reported per trace and scope | `src/evaluate_agents.py`; `src/aggregate_results.py` | four `results/v1/tables/<trace>/<scope>/seed_summary.csv` files | evidenced |
| C-006 | Statistics | Friedman, Kendall's W, Nemenyi, Wilcoxon CIs, Page trend, and CD inputs are produced | `src/statistical_test.py`; `docs/methodology_protocol.md` | `results/v1/tables/<trace>/statistics/` | evidenced |
| C-007 | Selection | Development selection uses configured Pareto metrics and CI tie-breakers | `src/select_best.py`; `config.yaml` | `results/v1/selection/{physical,deeplearn}.json` | evidenced |
| C-008 | Controls | Heuristics use no-backfill for the primary comparison; random is stochastic | `src/run_baseline.py`; `src/random_control.py`; `config.yaml` | `results/v1/tables/paper/*_vs_{baseline,random}.csv`; `backfill_bands.csv` | evidenced |
| C-009 | Findings | Physical DRL did not beat masked random; deeplearn leaders did not separate at ten seeds | `results/v1/README.md` | main, rank, random-comparison, and holdout tables in `results/v1/tables/paper/` | evidenced |
| C-010 | Provenance | Every public artifact is hashed and source-accounted | `scripts/validate_results_release.py`; `docs/result_schema.md` | `results/v1/manifest.json` | evidenced |

## Mandatory evidence buckets

- protocol and split policy: `docs/methodology_protocol.md`, `docs/data_split_policy.md`;
- executable workflow and contracts: `Snakefile`, `docs/result_schema.md`, `tests/`;
- aggregate and holdout evidence: `results/v1/tables/{physical,deeplearn}/`;
- statistics: `results/v1/tables/*/statistics/`;
- controls and paper claims: `results/v1/tables/paper/`;
- immutable provenance: `results/v1/manifest.json` and its validator.

The release caveats—historical unmasked truncation, duplicate physical timing observations, and unavailable historical statistics commit—must accompany any claim derived from v1.
