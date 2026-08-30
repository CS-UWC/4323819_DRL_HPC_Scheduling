# Results and Interpretation

[`results/v1/README.md`](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/results/v1/README.md) is the evidence authority for published findings and caveats. Read it first, then verify the immutable bundle:

```bash
python scripts/validate_results_release.py
```

The [manifest](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/results/v1/manifest.json) binds each artifact to its hash, source path, evidence scope, generation command, and available code commit.

## Evidence scopes

- **Development:** training, comparison, statistical analysis, and selection.
- **Holdout:** final reporting for all six frozen DRL treatments; never selection.
- **Paper-curated:** rounded tables and figures derived from the frozen source snapshot.

## Metrics

Lower is better for waiting, slowdown, and turnaround. Higher is better for CPU/GPU utilization. Primary claims use average waiting and average slowdown; maxima, turnaround, utilization, latency, wall time, and memory contextualize them.

The statistical roles are defined in the versioned [methodology protocol](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/docs/methodology_protocol.md): Friedman is omnibus, Kendall's W is effect size, Nemenyi is post-hoc, Wilcoxon intervals quantify paired differences, Page tests ordered trends, and Pareto plus CI tie-breakers selects on development.

## Findings

- **Physical:** no learned treatment outperformed masked random selection.
- **Deeplearn:** MaskablePPO improved tail behaviour, but leading treatments did not separate statistically at ten seeds.
- **Masking:** it enforced feasible actions and improved deployability, not general schedule quality.

Do not interpret a non-significant difference as equivalence. The release includes separately defined heuristic-equivalence tables.

## Caveats

The historical paper snapshot includes capped unmasked rows and two duplicate physical timing observations. Scheduling metrics for the duplicates agree; timing differs. Raw evaluations are excluded from the curated bundle. Exact scope and provenance limitations are recorded in the release README and manifest.
