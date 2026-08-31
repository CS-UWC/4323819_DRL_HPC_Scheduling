# Data and Splits

The repository contains two upstream HPCSim Slurm traces:

| Trace | Rows | Submit range | Partition |
|---|---:|---|---|
| `data/physical_job.csv` | 84,135 | 2022-09-23 to 2022-09-30 | physical |
| `data/deeplearn_job.csv` | 68,720 | 2021-09-20 to 2022-09-30 | deeplearn |

Cluster definitions are under `data/topology/`. Exact provenance, trace fields, node CSV, and switch-hierarchy formats are defined in [`docs/data.md`](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/docs/data.md).

## Generate deterministic splits

```bash
python -m src.make_split --src physical_job --ratio 0.7 --out-dir data/splits/
python -m src.make_split --src deeplearn_job --ratio 0.7 --out-dir data/splits/
```

For each trace, the script stable-sorts on `Submit`, places the earliest 70% in development and the latest 30% in holdout, and records metadata under `data/splits/logs/`.

```text
<trace>_dev70.tsv
<trace>_holdout30.tsv
logs/<trace>_r70.json
```

Never random-shuffle the trace. Tune and select on development only. All six frozen treatments may be evaluated on holdout once for final reporting; holdout must not feed selection. Training rejects paths containing holdout-like names.

The authoritative split and leakage rule is in [`docs/methodology_protocol.md`](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/docs/methodology_protocol.md).

## Governance

The traces contain operational scheduler fields and upstream-anonymized numeric user/group identifiers. Do not attempt re-identification or republish derived raw traces without checking the upstream HPCSim source, institutional policy, and applicable licensing. Generated split files are deliberately ignored rather than duplicated in Git.
