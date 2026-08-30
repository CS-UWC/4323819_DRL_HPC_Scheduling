# Intelligent Job Scheduling for HPC Systems
### A Statistical Evaluation of Deep Reinforcement Learning Approaches

**Justin M. Cheney** · University of the Western Cape · 2026

This repository is the authoritative implementation and reproducibility source for the study.

Over the past three decades, supercomputers and their workloads have become increasingly complex. Scheduling systems have evolved from traditional heuristics to Deep Reinforcement Learning (DRL) approaches that adapt policies to specific workloads. Though several studies develop DRL schedulers, no clear consensus exists on the optimal algorithm family. This project trains and evaluates representative algorithms from three DRL families — DQN, PPO, and A2C — with and without action masking, on real heterogeneous Slurm traces (~84k jobs). Statistical testing (Friedman, Nemenyi, Wilcoxon-based confidence intervals) determines whether significant performance differences exist across five industry-standard metrics.

---

## Dependencies

Only one of the following is needed to get started — the rest of the environment is installed automatically:
  
| Method | Requirement |
|--------|-------------|
| **Nix** (recommended) | [Nix](https://nixos.org/download/) with flakes enabled |
| **pip** (portability path) | Python ≥ 3.11 plus the system tools documented in [`docs/setup.md`](docs/setup.md) |

---

## Setup

### Nix (recommended)

Nix provides a fully reproducible, content-addressed environment — every dependency including the Python interpreter is pinned via `flake.lock`.

```bash
# 1. Install Nix (if not already installed)
sh <(curl -L https://nixos.org/nix/install) --daemon

# 2. Enable flakes (add to ~/.config/nix/nix.conf)
experimental-features = nix-command flakes

# 3. Enter the development shell
nix develop
```

All subsequent `just` and `python -m src.*` commands should be run inside `nix develop`.

### pip portability path

An unpinned `requirements.txt` derived from `flake.nix` is provided for environments where Nix is unavailable:

```bash
python -m pip install -r requirements.txt
```

See [`docs/setup.md`](docs/setup.md) for the additional system tools required by the workflow.

> Note: GPU support (CUDA) requires a compatible PyTorch installation for your platform. Under Nix, CUDA is handled automatically by the flake.

---

## Running the Pipeline

The full workflow is managed by [Snakemake](https://snakemake.readthedocs.io) and orchestrated through [`just`](https://just.systems) — a command runner that wraps the verbose Snakemake invocations into short, memorable commands. No need to remember `--configfile`, `--profile`, or `--cores` flags.

### Local

| Command | Description |
|---------|-------------|
| `just dry_run_smoke` | Validate the smoke DAG without running any jobs |
| `just run_smoke` | Smoke test — fast end-to-end validation (~200 steps) |
| `just run_full` | Full pipeline: train → eval → aggregate → stats |
| `just clean` | Remove outputs; preserve logs |
| `just clean_all` | Remove all outputs including logs (full reset) |

### Cluster (SLURM)

| Command | Description |
|---------|-------------|
| `just dry_run_slurm` | Validate the production DAG for cluster submission |
| `just dry_run_smoke_slurm` | Validate the smoke DAG for cluster submission |
| `just run_smoke_slurm` | Submit smoke test to SLURM |
| `just run_full_slurm` | Submit full pipeline to SLURM |

Run `just help` to see all available targets.

---

## Results

The full experiment is complete: six DRL treatments were evaluated with ten seeds on each of two traces. Development data was used for selection; all six treatments were then evaluated on the isolated time-ordered holdout for final reporting. A curated, provenance-checked results bundle will be added under `results/v1/` in the results-publication phase.

---

## HPCSim Environment

This project uses **HPCSim** — a lightweight, trace-driven Gymnasium environment for HPC scheduling research — as its simulation backend. HPCSim was developed by Wang et al. (2025).

For environment configuration, trace format, node file format, and topology format, see [`docs/HPCSim.md`](docs/HPCSim.md).

---

## Citations

```bibtex
@article{Wang2025_1,
  author    = {Lingfei Wang and Maria A. Rodriguez and Nir Lipovetzky},
  title     = {Optimizing {HPC} scheduling: a hierarchical reinforcement learning
               approach for intelligent job selection and allocation},
  journal   = {Journal of Supercomputing},
  year      = {2025},
  volume    = {81},
  number    = {8},
  month     = {June},
  publisher = {Springer},
  doi       = {10.1007/s11227-025-07396-3}
}
```

```bibtex
@article{Carrasco2020,
  author    = {Carrasco, Jac{\'i}nto and Garc{\'i}a, Salvador and Rueda, M Mar
               and Das, Swagatam and Herrera, Francisco},
  title     = {Recent trends in the use of statistical tests for comparing swarm
               and evolutionary computing algorithms: Practical guidelines and a
               critical review},
  journal   = {Swarm and Evolutionary Computation},
  volume    = {54},
  pages     = {100665},
  year      = {2020},
  publisher = {Elsevier}
}
```

```bibtex
@article{Mölder2025,
  author  = {M{\"o}lder, F and Jablonski, KP and Letcher, B and Hall, MB and
             van Dyken, PC and Tomkins-Tinch, CH and Sochat, V and Forster, J
             and Vieira, FG and Meesters, C and Lee, S and Twardziok, SO and
             Kanitz, A and VanCampen, J and Malladi, V and Wilm, A and
             Holtgrewe, M and Rahmann, S and Nahnsen, S and K{\"o}ster, J},
  title   = {Sustainable data analysis with Snakemake
             [version 3; peer review: 2 approved]},
  journal = {F1000Research},
  volume  = {10},
  number  = {33},
  year    = {2025},
  doi     = {10.12688/f1000research.29032.3}
}
```

```bibtex
@inproceedings{Dolstra2004,
  author    = {Dolstra, Eelco and de Jonge, Merijn and Visser, Eelco},
  title     = {Nix: A Safe and Policy-Free System for Software Deployment},
  booktitle = {Proceedings of the 18th USENIX Large Installation System
               Administration Conference (LISA)},
  year      = {2004},
  pages     = {79--92}
}
```
