# Data and HPCSim Environment

This file is the authority for dataset provenance and simulator input formats. Split and leakage rules live in [`methodology_protocol.md`](methodology_protocol.md).

## Data provenance

The repository distributes two tab-separated Slurm accounting traces obtained with the upstream HPCSim/HeraSched research artifacts:

| File | Rows | Submit range | SHA-256 |
|---|---:|---|---|
| `data/physical_job.csv` | 84,135 | 2022-09-23 to 2022-09-30 | `d3855a96f10efc33e163241aec510b65c10d13edf6c64861871dde420b20bdf8` |
| `data/deeplearn_job.csv` | 68,720 | 2021-09-20 to 2022-09-30 | `1f3ec6d7f4d34c10fbd07cd826e0df2fb55d94828ec62198bff3d2c788d7a936` |

Associated cluster inputs are:

- `data/topology/physical_topology.txt`;
- `data/topology/deeplearn_topology.txt`;
- `data/topology/nodes.csv`.

Original source:

- HeraSched/HPCSim: <https://gitlab.unimelb.edu.au/lingfeiw/herasched>
- Wang, Rodriguez, and Lipovetzky (2025), <https://doi.org/10.1007/s11227-025-07396-3>

The checked-in traces preserve upstream operational columns, including numeric user/group identifiers, account, partition, resource requests, timestamps, and final state. They are not simplified CSV exports.

## HPCSim

HPCSim is a trace-driven Gymnasium environment. Its observation combines cluster state with a queue window; selector actions choose jobs. This project fixes allocation to best-fit and trains only the selector. Maskable treatments prevent infeasible choices.

### Job trace format

Trace files are tab-separated. Key fields are:

| Field | Meaning |
|---|---|
| `JobID` | job identifier |
| `UID`, `GID`, `Account` | upstream-anonymized ownership fields |
| `AllocCPUS`, `AllocNodes`, `Allgpu`, `Allmem` | allocated resources |
| `ReqCPUS`, `ReqNodes`, `Reqgpu`, `ReqMem` | requested resources |
| `TimelimitRaw`, `ElapsedRaw` | requested and actual duration |
| `Submit`, `Start`, `End` | Slurm timestamps |
| `State`, `Partition` | final state and partition |

For remaining fields, see the [Slurm accounting documentation](https://slurm.schedmd.com/accounting.html).

### Node format

`data/topology/nodes.csv` describes compute nodes:

| Field | Meaning |
|---|---|
| `Features` | CPU features |
| `core` | cores per node |
| `memory` | memory in MB |
| `node_type` | node identifier |
| `gpu`, `gpu_number` | GPU model and count |
| `partition` | partition membership |

### Topology format

Topology files define the switch hierarchy:

```text
SwitchName=sp-266-p16-1 Level=1 LinkSpeed=1 Switches=le-266-q11-1-res,...
SwitchName=le-266-q11-1-res Level=0 LinkSpeed=1 Nodes=spartan-bm[053-066]
```

`Level=0` identifies edge switches. Higher levels use `Switches`; edge entries use `Nodes`.

## Deterministic split generation

Generated splits are ignored rather than duplicated in Git:

```bash
python -m src.make_split --src physical_job --ratio 0.7 --out-dir data/splits/
python -m src.make_split --src deeplearn_job --ratio 0.7 --out-dir data/splits/
```

The script stable-sorts on `Submit`, writes `*_dev70.tsv` and `*_holdout30.tsv`, and records source hash, row counts, ratio, sort key, split ID, timestamp, and paths under `data/splits/logs/`.

## Governance

The traces are upstream-anonymized scheduler records, not synthetic data. Do not attempt re-identification. Before redistributing raw or derived traces, verify the upstream license, institutional policy, and cluster-specific restrictions. The public results release contains aggregate evidence only.
