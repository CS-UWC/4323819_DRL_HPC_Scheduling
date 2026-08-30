# HPC / SLURM Workflow

## Preconditions

1. `just run_smoke physical` passes locally.
2. `just dry_run physical` resolves the production DAG.
3. Apptainer, `rsync`, SLURM, and the compatible NVIDIA host driver are available.
4. The container and scratch links exist.

## Build the container and prepare scratch

```bash
just build_sif
just setup_scratch
```

`setup_scratch` creates absolute links from `trained_model/`, `result/`, and `logs/` to `/scratch/$USER/DRL_HPC_Scheduling/`. The SLURM profile binds `/scratch` and runs the container with `--nv`.

## Validate and submit

Run one trace per invocation:

```bash
just dry_run_slurm physical
just run_full_slurm physical

just dry_run_slurm deeplearn
just run_full_slurm deeplearn
```

`run_full_slurm` includes development training/evaluation, statistics, controls, selection, and all-six holdout reporting. There is no separate `run_full_with_base_slurm` target.

Production scale is 60 training and 60 development-evaluation jobs per trace, plus controls and holdout evaluation. Each training run uses 3M steps. Resource defaults and retry policy live in [`profiles/slurm/config.yaml`](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/profiles/slurm/config.yaml).

## Monitor

```bash
squeue -u "$USER"
just slurm_report
```

Rule logs are under `logs/snakemake/<trace>/`.

## Archive

After selection has completed:

```bash
just archive_results physical
ARCHIVE=/path/to/archive just archive_results deeplearn
```

The idempotent archive copies the result tree, manifests, and every final model path recorded in the run manifest. `best_algorithm.json` gates model archiving but does not limit it to the winner.

## Completion checks

- all 60 training and 60 development-evaluation jobs completed;
- `aggregate/`, `stats/`, and `best/` are populated;
- all-six holdout seed and treatment summaries exist;
- control comparisons exist;
- metadata contains the injected Git commit;
- results and all final models are archived off purgeable scratch.

## Stuck SLURM job steps

The profile patches inner `srun` calls with `--overlap --immediate=300`. If a step remains stuck, collect:

```bash
scontrol show job <job-id>
scontrol show node <node-name>
```

Look for nodes in `COMPLETING`/`DRAIN` or a stuck prolog, then contact the cluster administrator. See [Troubleshooting](Troubleshooting).
