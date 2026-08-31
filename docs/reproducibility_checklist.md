# Reproducibility Checklist

Use this checklist for every experiment batch or published result.

## Required record

- environment: Nix/flake lock or explicitly labeled portability environment;
- Git commit, branch/tag, and working-tree state;
- source trace SHA-256, split ID, sort key, ratio, and row counts;
- algorithms, masking modes, seeds, timesteps, and hyperparameter source;
- exact command and UTC timestamp;
- output paths and schema validation result;
- development/holdout isolation confirmation;
- aggregate/statistics/release hash validation;
- reviewer, date, and unresolved limitations.

## Historical record: v1 artifact publication gate

| Field | Recorded value |
|---|---|
| Date | 2026-08-30 |
| Repository commit | `6f8755bc9e8d9e1260e2d576b39be5ce45adf3b9` (artifact-publication checkpoint; superseded by the final repository release below) |
| Branch / state | `main`; clean after commit |
| Experiment source commit | `fae1c739dd8e1743cd61d9cf909b23fa6e7d32a1` |
| Release base commit | `fa0e299b58fa5ce297bb52a439d82658330600df` |
| `flake.lock` SHA-256 | `b1f0527ee71e806fe82194d9f5233bc0acd91508d1420cd4811c577b8e615e17` |
| Production config snapshot | `results/v1/config/source_config.yaml`, SHA-256 `d786ca84879b2812a29441cd89203cc1df678a0f329d8a41d2cc1fed3dfcf2fe` |
| Physical source | 84,135 rows; SHA-256 `d3855a96f10efc33e163241aec510b65c10d13edf6c64861871dde420b20bdf8`; split `physical_job_r70` |
| Deeplearn source | 68,720 rows; SHA-256 `1f3ec6d7f4d34c10fbd07cd826e0df2fb55d94828ec62198bff3d2c788d7a936`; split `deeplearn_job_r70` |
| Matrix | six DRL treatments × ten fixed seeds × two traces; development and holdout summaries |
| Holdout rule | latest 30%; all six treatments reported; no tuning or selection |
| Release | `results/v1/`; released `2026-08-30T20:52:13Z` |
| Manifest SHA-256 | `be21e3ab945ff87bdf86ad359b81fa0c73b4cc5be92268daae0f6b5d8a484b4c` |

Commands and outcomes:

```bash
python -m unittest discover -s tests -v
# 8 tests passed

python scripts/validate_results_release.py
# Validated results/v1

snakemake --configfile config.smoke.yaml --config trace_name=physical_job --dry-run --quiet
snakemake --configfile config.smoke.yaml --config trace_name=deeplearn_job --dry-run --quiet
snakemake --configfile config.yaml --config trace_name=physical_job --dry-run --quiet
snakemake --configfile config.yaml --config trace_name=deeplearn_job --dry-run --quiet
# all four DAG dry-runs passed
```

Validation used Python 3.12 and Snakemake 9.3.4 from existing Nix-store packages. A fresh `nix develop` attempted to build the CUDA closure but did not finish within the 900-second validation window; therefore this record attests the release contracts, tests, and DAGs, not a clean-clone end-to-end retraining.

Reviewer outcome: parallel standards/spec review **PASS**. Known residual caveats are recorded in `results/v1/README.md` and `results/v1/manifest.json`.

## Completed record: Phase 4 documentation gate

On 2026-08-30, the Phase 4 tree passed 12 unit/contract checks, all four smoke/production × physical/deeplearn DAG dry-runs, `nix flake check --no-build`, shell syntax checks, local Markdown path/fragment checks, documented-`just` target checks, release validation, Python compilation, and `git diff --check`. The GitHub Wiki source is backed up under `wiki/` and was subsequently published by the repository owner.

## Completed record: Phase 5 cleanup gate

On 2026-08-31, `nix run .#test` passed 13 checks from a 53-path closure containing no Torch, CUDA, cuDNN, NCCL, or Triton paths. All four DAG dry-runs, `nix flake check --no-build`, release validation, shell syntax, and `git diff --check` passed. `git status --ignored` contained only intentional `.snakemake/` state and generated `data/splits/`; local Python caches were removed.

## Authoritative final-release record: Phase 6 clean-clone gate

Tag: `v1.0.0`

Verified code commit: `dead94fbd0eee7365cdac45382bcfbc182a441f1`. The `v1.0.0` tag adds only the final gate record and release metadata above that tested code commit.

A fresh clone passed:

- `nix run .#test`: 14 tests;
- `python scripts/validate_results_release.py` in `.#test`;
- Python compilation and `git diff --check`;
- smoke and production DAG dry-runs for `physical_job` and `deeplearn_job`;
- `nix develop -c just run_smoke physical`: all 28 rules completed.

The first clean-clone smoke attempt exposed a missing `TRAD_ALGORITHMS` import in `src.run_baseline`; `dead94f` adds the import and a red/green CLI regression test. The successful rerun produced four unique development and four unique holdout treatment-seed rows, all with finite core metrics and explicit `step_cap`/partial status. Aggregate row counts were 4 seed and 2 treatment summaries per scope. Development and holdout control summaries contained the expected two heuristics plus seeded random control. Aggregate and statistics metadata recorded the verified commit, and every terminal artifact existed.

All repository-relative README/results links resolved. Every external URL in `README.md` and `results/v1/README.md`, including the published Wiki pages, returned HTTP 2xx. The 2.4 MB immutable release remains tracked; no duplicate attachment is required.
