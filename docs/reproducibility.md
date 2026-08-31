# Reproducibility and Release Record

This file is the authority for run-record requirements and final release verification.

## Required record for every experiment

Capture:

- Nix `flake.lock` state or an explicitly labeled portability environment;
- Git commit, branch/tag, and working-tree state;
- source trace SHA-256, split ID, sort key, ratio, and row counts;
- treatment, masking mode, seed, timesteps, and hyperparameter source;
- exact command and UTC timestamp;
- output paths and schema-validation result;
- development/holdout isolation confirmation;
- aggregate/statistics/release hash validation;
- reviewer, date, and unresolved limitations.

## Frozen evidence provenance

| Item | Value |
|---|---|
| Experiment source commit | `fae1c739dd8e1743cd61d9cf909b23fa6e7d32a1` |
| Results publication base | `fa0e299b58fa5ce297bb52a439d82658330600df` |
| Production config snapshot | `results/v1/config/source_config.yaml`; SHA-256 `d786ca84879b2812a29441cd89203cc1df678a0f329d8a41d2cc1fed3dfcf2fe` |
| Physical trace | SHA-256 `d3855a96f10efc33e163241aec510b65c10d13edf6c64861871dde420b20bdf8`; split `physical_job_r70` |
| Deeplearn trace | SHA-256 `1f3ec6d7f4d34c10fbd07cd826e0df2fb55d94828ec62198bff3d2c788d7a936`; split `deeplearn_job_r70` |
| Matrix | six DRL treatments × ten seeds × two traces; development and holdout summaries |
| Release manifest | `results/v1/manifest.json`; SHA-256 `be21e3ab945ff87bdf86ad359b81fa0c73b4cc5be92268daae0f6b5d8a484b4c` |

`results/v1/manifest.json` is the per-file source/hash authority. Historical paper-generation scripts lacking a Git repository are preserved and hashed in `results/v1/provenance/scripts/`.

## Final v1.0.0 gate

Verified code commit: `dead94fbd0eee7365cdac45382bcfbc182a441f1`. Tag `v1.0.0` adds only final documentation and release metadata above that tested code commit.

A clean clone on 2026-08-31 passed:

- `nix run .#test`: 14 focused tests;
- `nix flake check --no-build`;
- Python compilation, shell syntax, and `git diff --check`;
- smoke and production DAG dry-runs for both traces;
- `python scripts/validate_results_release.py`;
- `nix develop -c just run_smoke physical`: all 28 rules completed.

The first clean-clone smoke attempt exposed a missing `TRAD_ALGORITHMS` import in `src.run_baseline`. Commit `dead94f` adds the import and a red/green CLI regression test. The successful rerun produced:

- four unique development and four unique holdout treatment-seed rows;
- finite core metrics with explicit `step_cap`/partial smoke metadata;
- four seed and two treatment summaries per DRL scope;
- expected deterministic heuristics plus two seeded random-control rows per control scope;
- aggregate/statistics metadata containing the verified commit;
- every terminal workflow artifact.

All repository-relative README/results links resolved. Every external URL in `README.md` and `results/v1/README.md`, including published Wiki pages, returned HTTP 2xx. The 2.4 MB immutable release remains tracked; no duplicate attachment is required.

## Evidence index

| Claim area | Authority | Published evidence |
|---|---|---|
| treatment design and statistics | `methodology_protocol.md`; `config.yaml` | `results/v1/manifest.json`; statistics tables |
| source data and environment | `data.md` | trace hashes and release summaries |
| split isolation | `methodology_protocol.md`; `src/make_split.py`; `Snakefile` | development/holdout seed summaries |
| workflow and schemas | `pipeline_contract.md`; tests | aggregate metadata and terminal artifacts |
| selection | `src/select_best.py`; configured Pareto keys | `results/v1/selection/` |
| controls | `src/run_baseline.py`; `src/random_control.py` | baseline/random comparison tables |
| paper findings and caveats | `results/v1/README.md` | `results/v1/tables/paper/` |
