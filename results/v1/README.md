# Results release v1

This is the curated, immutable evidence bundle used by the paper. It contains summary-level results and selected figures, not raw runs, checkpoints, logs, or generated split files.

## Key findings

- On the physical trace, no learned DRL treatment outperformed the masked random control; see [`physical_main.csv`](tables/paper/physical_main.csv) and [`physical_vs_random.csv`](tables/paper/physical_vs_random.csv).
- On the heterogeneous deeplearn trace, MaskablePPO improved tail behaviour but did not statistically separate from the other leading DRL treatments at ten seeds; see [`deeplearn_main.csv`](tables/paper/deeplearn_main.csv), [`deeplearn_vs_random.csv`](tables/paper/deeplearn_vs_random.csv), and the [rank figure](figures/deeplearn_cd_diagram_avg_waiting.png).
- Masking made policies deployable, but the experiment does not support a general schedule-quality advantage for one DRL family.
- All six DRL treatments were evaluated on the isolated holdout after development-only selection; see the [physical](tables/physical/holdout/algorithm_summary.csv) and [deeplearn](tables/deeplearn/holdout/algorithm_summary.csv) holdout summaries.

## Layout

- `config/source_config.yaml`: exact production configuration recovered from the recorded source commit.
- `tables/paper/`: compact tables used directly or substantively by the paper.
- `tables/<trace>/development/`: six-treatment aggregate and per-seed development results.
- `tables/<trace>/holdout/`: six-treatment aggregate and per-seed holdout results.
- `tables/<trace>/statistics/`: Nemenyi, Wilcoxon-CI, confidence-curve, Page-trend, and critical-difference inputs.
- `selection/`: frozen winner-selection rationale for each trace.
- `figures/`: PNG counterparts of the six figures imported by the paper.
- `provenance/scripts/`: exact paper-table and figure generation scripts from the frozen workspace.
- `manifest.json`: source path, source hash, release hash, scope, split, command, generation-script hash, and available code commit for every artifact.

## Interpretation caveats

The three unmasked DRL treatments did not complete full evaluation episodes and are dagger-marked in paper tables. Their values must not be interpreted as full-episode quality comparisons.

The physical source contains two duplicate treatment-seed evaluations in both development and holdout. Each duplicate pair has identical scheduling metrics but slightly different timing. The published seed summaries correctly contain 60 independent treatment-seed rows; timing for the affected seeds averages two observations. Details are recorded in [`manifest.json`](manifest.json).

Primary heuristic comparisons disable backfill so the heuristics and DRL policies have the same scheduling mechanism. The separate [`backfill_bands.csv`](tables/paper/backfill_bands.csv) reports sensitivity to enabling it.

## Validate

From the repository root:

```bash
python scripts/validate_results_release.py
```

The validator checks every declared file hash and verifies six treatments × ten seeds for development and holdout on both traces.
