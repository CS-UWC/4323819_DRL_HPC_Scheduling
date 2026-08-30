# Result Snapshot Decision — 2026-08-30

The release work will use the current local paper-supporting snapshot, not rerun or silently replace it:

- generated development summaries: `../cluster_results/{physical_jobs,deeplearn_jobs}/{aggregate,stats,best}/`;
- paper-curated tables: `../Submmisions/IEEE-ACM/data/results/`;
- paper-curated figures: `../Submmisions/IEEE-ACM/figures/results/`.

The aggregate metadata records source code commit `fae1c739dd8e1743cd61d9cf909b23fa6e7d32a1`. From the workspace root, deterministic tree hashes (sorted file SHA-256 records, excluding `*.bak*`) are:

- generated summary tree: `17fb28c852414ec28790827ac2ace4a265fd36b76f1188d2339920371b7b3a7e`;
- paper table tree: `f6ae9161fb65b0dfbf87b7ec6b7af95b38a0012656bcccea035e668cec66ff32`;
- paper figure tree: `8ce0f746324e1340a42b67403d55957491991509a864f2c2376632b1772f4989`.

These hashes freeze the source snapshot; they do not approve every file for publication. Phase 3 must create per-file provenance, reconcile the physical aggregate's 62 raw rows versus 60 seed summaries, and apply the holdout publication policy before copying artifacts into `results/v1/`.
