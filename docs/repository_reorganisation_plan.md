# Repository Reorganisation Plan

Status: Phases 0–6 complete; clean-clone gate passed, 2026-08-31

## Goal

Turn `Project_Github/` into the public, reproducible source repository for the completed study:

- publish a small, traceable results release;
- put the study's key facts, findings, quick start, and essential commands in the main README;
- move detailed step-by-step guides to the GitHub Wiki and link them from the README and repository;
- make setup and workflow instructions match the repository;
- remove stale and generated clutter;
- fix pipeline correctness risks before presenting the code as reproducible;
- leave one clear path from configuration to results.

This plan uses Matt Pocock's codebase-design vocabulary. The pipeline stages are modules whose interfaces are their CLI arguments and file contracts. Cleanup should increase locality at those file seams rather than add speculative adapters.

## Review summary

### Blockers identified by the review (resolved in Phases 0–4)

1. **Baseline output race**
   - `src/HPCsim/HPCsim.py` writes heuristic output to a fixed path.
   - `src/run_baseline.py` moves that file after each run.
   - Development and holdout baseline rules can run concurrently and overwrite or move each other's output.

2. **Non-idempotent run manifest**
   - `src/utils.py::write_manifest_entry` always appends a new run ID.
   - Retries can create duplicate treatment/seed rows and change downstream aggregation.

3. **Selection interface does not match its claims**
   - `src/select_best.py::filter_statistical_pareto` returns every Pareto candidate; its statistical “filter” removes nothing.
   - `config.yaml` defines Pareto metrics and tie-breakers, but the Snakefile does not pass them to the selector.

4. **Capped evaluations look complete**
   - `src/evaluate_agents.py` can stop at `max_steps` but writes ordinary result rows without completion metadata.
   - Production aggregation and selection cannot distinguish partial from full-trace evaluations.

5. **Results have no release provenance**
   - Complete generated results exist in `../cluster_results/` and curated paper tables in `../Submmisions/IEEE-ACM/`.
   - No manifest binds the public tables to a code commit, configuration, split metadata, command, and hashes.

6. **Holdout policy was contradictory**
   - The locked policy now evaluates all six frozen DRL treatments on holdout for final reporting.
   - Holdout remains excluded from training, tuning, and selection.

### Important documentation drift

- Workflow docs use `TRACE=...`, while `just` recipes take a positional trace argument.
- `just run_full_with_base_slurm` is documented but does not exist.
- Production run counts are stale: configuration has 10 seeds × 6 algorithms per trace.
- Trace and topology format descriptions disagree between `docs/data.md` and `docs/HPCSim.md`.
- README Conda instructions do not match the pip-format requirements file.
- Pip is presented as a complete environment but does not provide `just`, `rsync`, test, or formatting tools.
- Split-ID documentation includes timestamps, while `make_split.py` creates stable `<trace>_r70` IDs.
- README still says results are pending.
- `docs/submission2_evidence_map.md` and the reproducibility checklist remain stale templates.

## Target repository shape

```text
Project_Github/
├── README.md
├── LICENSE
├── CITATION.cff
├── flake.nix
├── flake.lock
├── requirements.txt
├── config.yaml
├── config.smoke.yaml
├── Snakefile
├── justfile
├── src/
├── tests/
├── data/
│   ├── topology/
│   └── README.md
├── results/
│   └── v1/
│       ├── README.md
│       ├── manifest.json
│       ├── tables/
│       └── figures/
├── docs/
│   ├── methodology_protocol.md
│   ├── data_split_policy.md
│   └── result_schema.md
├── profiles/slurm/
└── nix/
```

The README is the first-glance interface. It must stand on its own for understanding the project and running the shortest supported path. The GitHub Wiki holds longer tutorials, troubleshooting, cluster procedures, and other step-by-step material. Keep only version-coupled technical contracts and research protocols in `docs/`; do not duplicate the same guide across README, Wiki, and `docs/`.

Do not copy raw run outputs, models, TensorBoard logs, split files, or all generated plots into Git.

## Work plan

### Phase 0 — Lock decisions

Before code or publication changes:

- [x] Declare `Project_Github/` the authoritative implementation repository and update the workspace `AGENTS.md` and root `README.md` accordingly.
- [x] Decide and document holdout scope: all six treatments for final reporting, with no holdout tuning or selection.
- [x] Freeze the release experiment definition: two traces, six DRL treatments, three deterministic heuristics, one random control, and ten seeds for stochastic treatments.
- [x] Select and hash the source result snapshot that supports the paper; per-file release provenance remains Phase 3 work.

**Exit check:** one short decision record states the authoritative repo, holdout policy, treatment set, seeds, traces, and source result snapshot.

### Phase 1 — Fix correctness before cleanup

- [x] Remove the fixed-path baseline race at its source by letting the HPCSim result writer accept an output path.
- [x] Make manifest writes idempotent on `(split_id, treatment_id, seed)` and reject conflicting duplicates.
- [x] Record evaluation completion status, requested cap, actual decisions, and completed jobs.
- [x] Reject capped/partial evaluations from production aggregation; permit them only through the smoke workflow's explicit flag.
- [x] Rename and implement the selection method honestly as Pareto plus CI-based tie-breaking; Nemenyi remains reported evidence, not an elimination rule.
- [x] Pass configured Pareto metrics and tie-breakers through the selector interface.
- [x] Guard optional `--split_id` handling in `src/train_agents.py`.
- [x] Replace empty `baseline_metadata.json` with an honestly named completion marker.
- [x] Delete the shared per-job `eval_summary.json` write.

**Exit check:** a clean smoke workflow cannot create duplicate runs, confuse partial evaluations with complete results, or race baseline files.

### Phase 2 — Add the smallest regression checks

Create focused tests at the high-leverage file seams:

- [x] manifest rerun preserves one canonical row;
- [x] baseline output paths are caller-controlled and isolated;
- [x] partial evaluation is marked and refused by production aggregation;
- [x] selector returns the declared winner for a tiny CSV fixture;
- [x] configured selector metrics are honoured;
- [x] smoke and production DAG dry-runs succeed for both traces.

Avoid broad unit-test scaffolding. These interface-level checks should survive internal refactors.

**Exit check:** one documented command runs all checks locally.

### Phase 3 — Publish a curated results release (complete)

`results/v1/` is published from the frozen snapshot with per-file hashes, source paths, available commits and commands, experiment metadata, and explicit provenance caveats.

Publish:

- aggregate algorithm and seed summaries for both traces;
- the statistical tables used by the paper;
- winner-selection rationale;
- paper-facing summary, rank, cost, baseline-comparison, and equivalence tables;
- only the figures used in the paper or README.

Do not publish:

- `eval_runs/runs/` or `holdout/runs/`;
- `*_metrics.raw.csv`;
- `_legacy_prenaming/`;
- TensorBoard logs;
- models/checkpoints;
- generated split files or duplicate raw traces;
- raw holdout runs; only the approved six-treatment seed and algorithm summaries are published.

`results/v1/manifest.json` must record:

- source code commit;
- source paths under `cluster_results/` and `Submmisions/IEEE-ACM/`;
- configuration and split IDs;
- treatment and seed lists;
- generation commands;
- UTC release timestamp;
- SHA-256 for every published table and figure;
- whether each artifact is development, holdout, or paper-curated evidence.

**Exit check:** complete — README result claims link to versioned artifacts, and `python scripts/validate_results_release.py` verifies the release manifest and experiment shape.

### Phase 4 — Build the README and Wiki information architecture

- [x] Make README the complete first glance: research question, experiment design, key findings, repository layout, requirements, shortest quick start, essential local and SLURM commands, published results, citation, limitations, and links to detailed Wiki guides.
- [x] Keep README concise enough to scan, but do not make readers open the Wiki to understand the project, its results, or the basic reproduction path.
- [x] Create Wiki pages for detailed setup, local workflow, HPC/SLURM workflow, data preparation, configuration reference, result interpretation, troubleshooting, and contribution procedures.
- [x] Add a Wiki home page that follows the same task order as the README and links back to versioned repository files where appropriate.
- [x] Keep methodology, split policy, and machine-readable output contracts in version-controlled `docs/`; link to them from the Wiki rather than copying their contents.
- [x] Add stable README and repository links to the Wiki. Record the Wiki repository URL and ownership so its pages can be reviewed and backed up.
- [x] Correct `just` examples to use positional trace arguments.
- [x] Remove the nonexistent SLURM target.
- [x] Standardise run counts and holdout wording.
- [x] Make Nix the authoritative path; describe pip as a portability path with explicit system prerequisites.
- [x] Remove the invalid `conda install --file requirements.txt` command.
- [x] State GPU driver and Apptainer `--nv` requirements accurately.
- [x] Make `docs/HPCSim.md` the authoritative trace/topology format description; reduce `docs/data.md` to provenance and links.
- [x] Replace data placeholders and the placeholder repository URL.
- [x] Update the evidence map and include one completed reproducibility record.
- [x] Align archive documentation with all final models being retained after selection.

**Exit check:** a new visitor can understand the study and run the shortest supported workflow from README alone; every detailed Wiki procedure is linked, non-duplicated, and tested; every documented command exists and passes a dry run in its stated environment.

### Phase 5 — Remove dead interfaces and clutter

- [x] Delete or wire unused configuration: removed `allocators`, smoke `topology_file`, and visualisation toggles; Pareto keys remain because the Snakefile passes them to selection.
- [x] Replace stale TODO and command references in module documentation.
- [x] Remove the obsolete `src/test_scheduler.py` CLI in favor of `src.run_baseline`.
- [x] Remove generated `__pycache__/` directories locally.
- [x] Ignore `.snakemake/`, virtual environments, `build.log`, container tar files, and other generated outputs.
- [x] Remove placeholder duplicate data directories; retain the two required source traces and singular `data/topology/` inputs while generated splits remain ignored.
- [x] Add `CITATION.cff`.

**Exit check:** `git status --ignored` shows only intentional generated files and no tracked duplicate outputs.

### Phase 6 — Final reproducibility gate

Completed from a clean clone of `dead94fbd0eee7365cdac45382bcfbc182a441f1`:

- [x] enter the documented Nix environment;
- [x] run compilation, shell syntax, and diff checks;
- [x] pass 14 focused contract tests through the lightweight test app;
- [x] resolve smoke and production DAGs for both traces;
- [x] complete one 28-rule physical end-to-end smoke workflow;
- [x] verify development/holdout/control schemas, expected row counts, finite core metrics, explicit smoke caps, and commit provenance;
- [x] verify every `results/v1/manifest.json` hash;
- [x] resolve every local README/results link and receive HTTP 2xx for every external README/results link.

**Exit check:** passed. `results/v1/` is about 2.4 MB and remains tracked, so no duplicate release attachment is needed. Tag `v1.0.0` identifies the verified repository release.

## Proposed PR sequence

1. `fix/pipeline-result-integrity`
2. `test/pipeline-contracts`
3. `results/v1-publication`
4. `docs/readme-and-wiki`
5. `docs/public-reproducibility`
6. `chore/repository-cleanup`

Keep correctness, results publication, documentation, and deletion in separate PRs so each change has a clear review surface.

## Deferred unless evidence requires it

- package-wide architectural rewrite;
- new plugin or adapter framework;
- migration away from Snakemake/just/Nix;
- publishing checkpoints or raw per-run outputs;
- adding multiple environment managers beyond the existing portability path.
