# Contributing

## Prepare a change

```bash
git clone https://github.com/JCheney20/DRL_HPC_Scheduling.git
cd DRL_HPC_Scheduling
nix develop
git switch -c <type>/<short-name>
```

Keep changes focused. Preserve development/holdout isolation and the machine-readable file contracts.

## Required checks

```bash
python -m unittest discover -s tests -v
just dry_run_smoke physical
just dry_run_smoke deeplearn
just run_smoke physical
python scripts/validate_results_release.py
```

Add one focused behavioral test when changing a parser, branch, loop, or pipeline contract. Do not add generated splits, raw evaluations, checkpoints, logs, or caches.

## Documentation ownership

- README: first glance and shortest supported path.
- Wiki: detailed procedures and troubleshooting.
- `docs/`: versioned methodology, split, HPCSim, DAG, and result contracts.
- `results/vN/`: immutable evidence; publish a new version instead of editing an established release.

Update commands where they are owned. `just help`, configs, and the Snakefile are executable authorities.

## Pull request

Include:

- purpose and smallest implemented change;
- changed files;
- commands run and their outcomes;
- result/provenance impact;
- residual risks.

For a bug report, provide the Git commit, environment path (Nix or pip), exact command, trace and split ID, expected and actual behavior, and relevant logs. Remove private paths or scheduler identifiers before posting.
