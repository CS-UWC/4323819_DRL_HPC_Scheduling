# Troubleshooting

## Python cannot import `src`

Run entry points from the repository root as modules:

```bash
python -m src.train_agents --help
```

Do not run `python src/train_agents.py`.

## Missing Python packages

Enter `nix develop`. On the pip path, reinstall `requirements.txt`; `sb3-contrib` is separate from stable-baselines3.

## CUDA is unavailable

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

Confirm a compatible NVIDIA host driver. Container jobs additionally require Apptainer `--nv`, already configured in the SLURM profile.

## Split is missing

```bash
python -m src.make_split --src physical_job --ratio 0.7 --out-dir data/splits/
```

## Holdout training is rejected

This is intentional. Train only on `*_dev70.tsv`; holdout is final-reporting evidence.

## DQN runs out of memory

For smoke diagnosis, reduce `buffer_size` and `n_envs`. Do not silently change production hyperparameters; record any changed configuration as a new run.

## Aggregation rejects an evaluation

Production requires `evaluation_complete=true` and rejects capped rows. Only `config.smoke.yaml` sets `allow_partial_evaluation: true`.

## Missing Git commit in metadata

Run from a Git checkout. On SLURM, start Snakemake on the login node so the Snakefile can inject `GIT_COMMIT` into container jobs.

## SLURM job is stuck

```bash
squeue -u "$USER"
scontrol show job <job-id>
scontrol show node <node-name>
```

A node stuck in `COMPLETING`/`DRAIN` or a hung prolog needs administrator attention. The profile retries transient failures twice.

## Nix reports an unfree package

The flake enables unfree packages for its package set. If a separate local Nix command still fails, set `{ allowUnfree = true; }` in `~/.config/nixpkgs/config.nix`.
