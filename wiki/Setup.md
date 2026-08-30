# Setup

## Nix (supported reproducibility path)

The flake targets `x86_64-linux` and pins the complete development environment.

```bash
curl -L https://nixos.org/nix/install | sh -s -- --daemon
mkdir -p ~/.config/nix
printf 'experimental-features = nix-command flakes\n' >> ~/.config/nix/nix.conf

git clone https://github.com/JCheney20/DRL_HPC_Scheduling.git
cd DRL_HPC_Scheduling
nix develop
```

Verify imports and the workflow interface:

```bash
python -c "import torch, stable_baselines3, sb3_contrib, gymnasium, scipy, paretoset; print('imports OK')"
just dry_run_smoke physical
```

Run Python entry points as modules from the repository root: `python -m src.<name>`.

## pip portability path

Pip is not a bit-for-bit reproduction environment. Use Python 3.11 or newer:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Install these system tools separately when needed:

| Tool | Needed for |
|---|---|
| `just` | documented command shortcuts |
| Graphviz `dot` | DAG export |
| `rsync` | scratch setup and result archiving |
| Apptainer/Singularity | cluster container execution |

Without `just`, call Snakemake directly, for example:

```bash
snakemake --configfile config.smoke.yaml --config trace_name=physical_job --dry-run
```

## GPU and container requirements

Nix uses `torch-bin`, whose wheel includes the user-space CUDA runtime. GPU execution still needs a compatible host NVIDIA driver; a CPU-only host may report CUDA unavailable.

```bash
python -c "import torch; print('CUDA available:', torch.cuda.is_available())"
```

The SLURM profile passes Apptainer `--nv` to expose the host driver and binds `/scratch`. See [HPC / SLURM Workflow](HPC-SLURM-Workflow).
