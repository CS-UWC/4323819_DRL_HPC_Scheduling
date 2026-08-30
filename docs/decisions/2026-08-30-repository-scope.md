# Repository Scope Decisions — 2026-08-30

- `Project_Github/` is the authoritative implementation and reproducibility repository.
- Final reporting evaluates all six DRL treatments on the time-ordered holdout. The holdout remains excluded from training, tuning, and selection.
- The frozen release experiment uses two traces; six DRL treatments; three deterministic heuristic baselines (LCFS, SJF, and UNICEP); one seeded random control; and ten seeds for every stochastic treatment. The primary controlled comparison disables heuristic backfill; both backfill modes were evaluated only to report the sensitivity band.
- The paper-supporting source snapshot is frozen in `2026-08-30-result-snapshot.md`; publication still requires per-file provenance and reconciliation.
- GitHub Wiki content is deferred for local preparation in the documentation phase; this repository remains the source for version-coupled protocols and output contracts.
