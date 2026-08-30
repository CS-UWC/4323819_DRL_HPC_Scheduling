# Deep Reinforcement Learning for HPC Job Scheduling: A Statistical Evaluation

This project asks which low-resource DRL family, with or without action masking, best schedules heterogeneous HPC workloads. It compares PPO, A2C, DQN, MaskablePPO, MaskableA2C, and MaskableDQN on two real Slurm traces.

| Design item | Value |
|---|---|
| Traces | `physical_job` and `deeplearn_job` |
| Split | Earliest 70% development; latest 30% holdout |
| Production | 10 seeds, 3M steps per treatment run |
| Selection | Development only; all six treatments reported on holdout |
| Primary metrics | Average waiting and average slowdown |

## Main findings

The [v1 release README](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/results/v1/README.md) is the evidence authority for these summaries and caveats.

- No learned treatment beat masked random selection on the physical trace.
- MaskablePPO improved deeplearn tail behaviour, but the leaders did not separate statistically at ten seeds.
- Masking prevented invalid choices; it did not generally improve schedule quality.

Read the [curated release](https://github.com/JCheney20/DRL_HPC_Scheduling/tree/main/results/v1) and [provenance manifest](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/results/v1/manifest.json).

## Quick start

```bash
nix develop
just dry_run_smoke physical
just run_smoke physical
```

Then follow:

1. [Setup](Setup)
2. [Local Workflow](Local-Workflow)
3. [HPC / SLURM Workflow](HPC-SLURM-Workflow)
4. [Data and Splits](Data-and-Splits)
5. [Configuration Reference](Configuration-Reference)
6. [Results and Interpretation](Results-and-Interpretation)
7. [Troubleshooting](Troubleshooting)
8. [Contributing](Contributing)

The repository README gives the complete first glance. Versioned research rules remain in the [methodology protocol](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/docs/methodology_protocol.md), [split policy](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/docs/data_split_policy.md), [HPCSim format specification](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/docs/HPCSim.md), and [result schema](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/docs/result_schema.md).

[Back to the authoritative repository](https://github.com/JCheney20/DRL_HPC_Scheduling)
