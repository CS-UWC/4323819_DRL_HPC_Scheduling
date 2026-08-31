# Deep Reinforcement Learning for HPC Job Scheduling: A Statistical Evaluation

**Justin M. Cheney · University of the Western Cape · 2026**

This is the authoritative implementation and reproducibility repository for a statistical comparison of low-resource deep reinforcement learning (DRL) schedulers. The study asks which DRL family, with or without action masking, best schedules heterogeneous HPC workloads while retaining at least 90% of full-model performance.

## Study at a glance

| Item | Design |
|---|---|
| Treatments | PPO, A2C, DQN, MaskablePPO, MaskableA2C, MaskableDQN |
| Workloads | `physical_job` (84,135 jobs) and `deeplearn_job` (68,720 jobs) |
| Split | Earliest 70% development; latest 30% isolated holdout; no shuffle |
| Production scale | 10 seeds × 6 treatments × 2 traces; 3M training steps per run |
| Controls | LCFS, SJF, UNICEP, and masked uniform-random selection |
| Primary metrics | Average waiting time and average slowdown |
| Analysis | Friedman, Kendall's W, Nemenyi, Wilcoxon CIs, Page trend, and Pareto selection |

Development data is the only surface used for model selection. All six treatments are evaluated on holdout for final reporting, but the holdout is never used for tuning or selection. See the versioned [methodology protocol](docs/methodology_protocol.md).

## Findings

[`results/v1/README.md`](results/v1/README.md) is the evidence authority for these summaries and their caveats.

- **Physical trace:** no learned treatment outperformed the masked random control ([summary](results/v1/tables/paper/physical_main.csv), [paired comparison](results/v1/tables/paper/physical_vs_random.csv)).
- **Deeplearn trace:** MaskablePPO improved tail behaviour, but the leading treatments did not separate statistically at ten seeds ([summary](results/v1/tables/paper/deeplearn_main.csv), [ranks](results/v1/figures/deeplearn_cd_diagram_avg_waiting.png)).
- **Overall:** masking chiefly supplied deployability by preventing invalid actions; it did not provide a general schedule-quality advantage.

The curated [`results/v1/`](results/v1/) release contains the paper-facing tables, summaries, figures, selection rationale, and a machine-readable [provenance manifest](results/v1/manifest.json). Verify it with:

```bash
python scripts/validate_results_release.py
```

## Requirements

**Nix is the reproducibility path.** The flake currently targets `x86_64-linux` and pins Python, PyTorch, Snakemake, `just`, Graphviz, and the analysis stack.

```bash
nix develop
```

The pip path is best-effort portability for Python 3.11+:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Pip does not install `just`, Graphviz, Apptainer, or `rsync`; install the tools needed by your workflow separately. GPU execution requires a compatible host NVIDIA driver. The Nix environment uses `torch-bin`'s bundled user-space CUDA runtime, while SLURM container jobs expose the host driver with Apptainer `--nv`.

Detailed setup: [Wiki Setup](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki/Setup) ([reviewable source](wiki/Setup.md)).

## Shortest reproduction path

From the repository root:

```bash
nix develop
just dry_run_smoke physical
just run_smoke physical
```

This runs the small, capped integration workflow; it validates file contracts, not scientific performance. Generated outputs land under `result/physical_job/` and are not committed.

### Essential commands

```bash
# Local
just dry_run physical
just run_full physical
just run_full deeplearn

# SLURM / Apptainer
just dry_run_slurm physical
just run_full_slurm physical
just run_full_slurm deeplearn

# Checks (lightweight Nix environment; no PyTorch/CUDA)
nix run .#test
python scripts/validate_results_release.py
```

Trace arguments are positional: use `just run_full deeplearn`, not `TRACE=deeplearn`. `just help` is the command authority.

## Repository layout

```text
Snakefile, config*.yaml  workflow and experiment configuration
src/                    simulator, training, evaluation, aggregation, and statistics
tests/                  focused pipeline-contract checks
data/                    distributable source traces and cluster topology
docs/                    versioned protocols and file contracts
wiki/                    reviewable source for the GitHub Wiki
profiles/slurm/          Snakemake SLURM profile
results/v1/              immutable curated evidence release
```

Dataset provenance and HPCSim formats are defined in [`docs/data.md`](docs/data.md); workflow and output schemas are defined in [`docs/pipeline_contract.md`](docs/pipeline_contract.md); verified release evidence is recorded in [`docs/reproducibility.md`](docs/reproducibility.md).

## Detailed guides

The [GitHub Wiki](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki) follows the same task order as this README:

- [Setup](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki/Setup)
- [Local workflow](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki/Local-Workflow)
- [HPC / SLURM workflow](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki/HPC-SLURM-Workflow)
- [Data and splits](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki/Data-and-Splits)
- [Configuration reference](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki/Configuration-Reference)
- [Results and interpretation](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki/Results-and-Interpretation)
- [Troubleshooting](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki/Troubleshooting)
- [Contributing](https://github.com/JCheney20/DRL_HPC_Scheduling/wiki/Contributing)

The published Wiki is backed up as reviewable source under [`wiki/`](wiki/README.md).

## Limitations

- The two workloads come from one upstream HPCSim/Slurm source and do not establish cross-centre generality.
- Ten seeds limit power for small pairwise effects.
- Historical unmasked evaluations contain documented truncation, and the physical source snapshot contains two duplicate timing observations; neither issue is hidden in the release.
- The published bundle excludes raw runs and checkpoints to avoid duplicating large generated artifacts.

See [`results/v1/README.md`](results/v1/README.md) for the full release caveats.

## Citation

GitHub-compatible citation metadata is available in [`CITATION.cff`](CITATION.cff).

```bibtex
@thesis{Cheney2026DRLScheduling,
  author      = {Justin M. Cheney},
  title       = {Deep Reinforcement Learning for HPC Job Scheduling:
                 A Statistical Evaluation},
  institution = {University of the Western Cape},
  type        = {Honours thesis},
  year        = {2026},
  url         = {https://github.com/JCheney20/DRL_HPC_Scheduling}
}
```

HPCSim is derived from Wang, Rodriguez, and Lipovetzky (2025), [doi:10.1007/s11227-025-07396-3](https://doi.org/10.1007/s11227-025-07396-3).

## License

Code is released under the [MIT License](LICENSE). Dataset use remains subject to the upstream source and institutional conditions described in [`docs/data.md`](docs/data.md).
