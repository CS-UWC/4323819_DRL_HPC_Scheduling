# Local Workflow

## Fast integration check

Inside `nix develop`:

```bash
just dry_run_smoke physical
just run_smoke physical
just dry_run_smoke deeplearn
just run_smoke deeplearn
```

The trace is a positional argument. Do not use `TRACE=...`.

Smoke configuration exercises two algorithms and two seeds for 200 steps, with evaluation capped at five decisions. It checks the DAG and file contracts; it does not produce publishable performance evidence.

## Production workflow

```bash
just dry_run physical
just run_full physical
just dry_run deeplearn
just run_full deeplearn
```

Production uses six treatments × ten seeds, 3M training steps per run, complete development evaluation, development-only selection, and all-six holdout reporting.

## Stage order for diagnosis

Prefer Snakemake. For a single-stage diagnosis, the order is:

1. split;
2. train;
3. evaluate development;
4. aggregate;
5. statistics;
6. select;
7. evaluate all treatments on holdout;
8. aggregate holdout and controls.

Create a split directly with:

```bash
python -m src.make_split --src physical_job --ratio 0.7 --out-dir data/splits/
```

Training must target `data/splits/*_dev70.tsv`. `src.train_agents` rejects holdout-like paths before environment construction.

## Expected outputs

```text
data/splits/                       generated and ignored
trained_model/<trace>/             checkpoints and completion markers
result/<trace>/eval_runs/          development evaluations
result/<trace>/aggregate/          seed and treatment summaries
result/<trace>/stats/              statistical outputs
result/<trace>/best/               selection rationale
result/<trace>/holdout/            final-reporting summaries
logs/                              manifests and rule logs
```

## Smoke gate

- both DAG dry-runs resolve;
- training completes without non-finite rewards;
- maskable policies receive valid masks;
- evaluation writes completion metadata;
- aggregation and statistics accept their inputs;
- run metadata records a non-null Git commit.

For file contracts, use the versioned [result schema](https://github.com/JCheney20/DRL_HPC_Scheduling/blob/main/docs/result_schema.md).
