# Repository Reorganisation Plan

Status: Phase 0–1 implemented and locally contract-tested, 2026-08-30

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

### Blockers identified by the review

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

6. **Holdout policy is contradictory**
   - Documentation says winner-only holdout evaluation.
   - The current Snakefile and `cluster_results/` evaluate all six DRL treatments on holdout.
   - This must be resolved before publishing holdout outputs.

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

- [ ] Make README the complete first glance: research question, experiment design, key findings, repository layout, requirements, shortest quick start, essential local and SLURM commands, published results, citation, limitations, and links to detailed Wiki guides.
- [ ] Keep README concise enough to scan, but do not make readers open the Wiki to understand the project, its results, or the basic reproduction path.
- [ ] Create Wiki pages for detailed setup, local workflow, HPC/SLURM workflow, data preparation, configuration reference, result interpretation, troubleshooting, and contribution procedures.
- [ ] Add a Wiki home page that follows the same task order as the README and links back to versioned repository files where appropriate.
- [ ] Keep methodology, split policy, and machine-readable output contracts in version-controlled `docs/`; link to them from the Wiki rather than copying their contents.
- [ ] Add stable README and repository links to the Wiki. Record the Wiki repository URL and ownership so its pages can be reviewed and backed up.
- [ ] Correct `just` examples to use positional trace arguments.
- [ ] Remove the nonexistent SLURM target.
- [ ] Standardise run counts and holdout wording.
- [ ] Make Nix the authoritative path; describe pip as a portability path with explicit system prerequisites.
- [ ] Remove the invalid `conda install --file requirements.txt` command.
- [ ] State GPU driver and Apptainer `--nv` requirements accurately.
- [ ] Make `docs/HPCSim.md` the authoritative trace/topology format description; reduce `docs/data.md` to provenance and links.
- [ ] Replace data placeholders and the placeholder repository URL.
- [ ] Update the evidence map and include one completed reproducibility record.
- [ ] Align archive documentation with whether all models or only the winner are retained.

**Exit check:** a new visitor can understand the study and run the shortest supported workflow from README alone; every detailed Wiki procedure is linked, non-duplicated, and tested; every documented command exists and passes a dry run in its stated environment.

### Phase 5 — Remove dead interfaces and clutter

- [ ] Delete or wire unused configuration: `allocators`, smoke `topology_file`, visualisation toggles, and Pareto keys.
- [ ] Replace stale TODO references in module docstrings with current documentation paths.
- [ ] Decide whether `src/test_scheduler.py` is a test or a CLI; rename or remove it accordingly.
- [ ] Remove generated `__pycache__/` directories locally.
- [ ] Ignore `.snakemake/`, virtual environments, `build.log`, container tar files, and other generated outputs.
- [ ] Review duplicate data locations (`data/physical_job.csv`, `data/deeplearn_job.csv`, generated splits) and keep only inputs that can legally and usefully be distributed.
- [ ] Add `CITATION.cff`.

**Exit check:** `git status --ignored` shows only intentional generated files and no tracked duplicate outputs.

### Phase 6 — Final reproducibility gate

Run from a clean clone:

1. enter the documented environment;
2. run formatting/static checks chosen in Phase 2;
3. run focused tests;
4. run smoke DAG dry-runs for both traces;
5. run one end-to-end smoke workflow;
6. verify output schemas and finite metrics;
7. regenerate or verify `results/v1/manifest.json` hashes;
8. check every README and results link.

**Exit check:** tag the verified release and attach the immutable results bundle if Git size makes tracked figures/tables unsuitable.

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
