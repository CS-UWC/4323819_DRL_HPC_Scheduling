# Dataset Provenance

This repository distributes two tab-separated Slurm accounting traces obtained with the upstream HPCSim/HeraSched research artifacts:

| File | Rows | Submit range | Size |
|---|---:|---|---:|
| `data/physical_job.csv` | 84,135 | 2022-09-23 to 2022-09-30 | ~22 MB |
| `data/deeplearn_job.csv` | 68,720 | 2021-09-20 to 2022-09-30 | ~20 MB |

Associated cluster inputs are:

- `data/topology/physical_topology.txt`;
- `data/topology/deeplearn_topology.txt`;
- `data/topology/nodes.csv`.

[`docs/HPCSim.md`](HPCSim.md) is the sole format authority for traces, nodes, and topology. This page records provenance only; it deliberately does not maintain a second schema.

## Source

Original environment and trace source:

- HeraSched/HPCSim: <https://gitlab.unimelb.edu.au/lingfeiw/herasched>
- Wang, Rodriguez, and Lipovetzky (2025), <https://doi.org/10.1007/s11227-025-07396-3>

The checked-in files preserve the upstream operational columns, including numeric `UID`/`GID`, account, partition, resource requests, timestamps, and final job state. They have not been rewritten into a simplified schema.

## Split generation

Generated train/holdout files are intentionally not committed. Recreate them deterministically:

```bash
python -m src.make_split --src physical_job --ratio 0.7 --out-dir data/splits/
python -m src.make_split --src deeplearn_job --ratio 0.7 --out-dir data/splits/
```

The script stable-sorts on `Submit`, writes earliest-70% development and latest-30% holdout files, and records metadata under `data/splits/logs/`. The authoritative governance rules are in [`docs/data_split_policy.md`](data_split_policy.md).

## Governance

The traces contain upstream-anonymized scheduler records, not synthetic data. Do not attempt re-identification. Before redistributing raw or derived traces, verify the upstream repository's current license, institutional data policy, and any cluster-specific restrictions. The public results release contains only aggregate summaries and paper-facing evidence.
