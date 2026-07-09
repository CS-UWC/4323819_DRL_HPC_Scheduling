#!/usr/bin/env bash
#
# clean_algo.sh <algorithm> — wipe every artifact for ONE algorithm so that
# `just run_full_slurm` retrains and re-evaluates only it, cleanly.
#
# Why this exists: the run manifest (logs/run_log.csv) is append-only, so
# retraining a *completed* algorithm appends duplicate run_id rows that break
# aggregate's uniqueness check. Failed/timed-out jobs never wrote a row, so
# they are safe — but to rerun a finished algorithm (e.g. after a code fix) we
# must first drop its rows and delete its models/markers. Snakemake keys on
# output-file existence, so removing the markers is enough for it to redo the
# train + eval; it then cascades aggregate/stats/holdout on its own.
#
# Matching is exact per algorithm: 'a2c' never touches 'maskable_a2c' artifacts
# (dir segments and filename prefixes are anchored, manifest match is column-
# exact).
#
# Usage:   scripts/clean_algo.sh maskable_a2c
#          DRYRUN=1 scripts/clean_algo.sh maskable_a2c   # show, delete nothing
#          TRACE_NAME=deeplearn_job scripts/clean_algo.sh a2c
set -euo pipefail

ALGO="${1:-}"
TRACE="${TRACE_NAME:-physical_job}"
MANIFEST="logs/run_log.csv"
VALID="dqn a2c ppo maskable_dqn maskable_a2c maskable_ppo"

case " $VALID " in
  *" $ALGO "*) ;;
  *) echo "usage: $0 <algorithm>   (one of: $VALID)" >&2; exit 1 ;;
esac

if [ "${DRYRUN:-0}" = 1 ]; then
  RM=(echo "  [dry-run] would remove:"); DEL=(-print); echo "== DRY RUN (nothing deleted) =="
else
  RM=(rm -rfv); DEL=(-print -delete)
fi

echo "Clearing algorithm '$ALGO' (trace '$TRACE')"

# 1. Trained models + their .train_complete markers (whole per-algo dir; the
#    dir segment is an exact name, so 'a2c' won't match the 'maskable_a2c' dir).
for d in trained_model/"$TRACE"/*/"$ALGO"; do
  [ -e "$d" ] && "${RM[@]}" "$d"
done

# 2. Eval completion markers: .seed_<seed>_<algo>_complete. Anchored regex
#    ([0-9]+ between the seed and the algo) so 'a2c' can't match a marker whose
#    algo segment is 'maskable_a2c'.
find "result/$TRACE/eval_runs" -maxdepth 1 -regextype posix-extended \
  -regex ".*/\.seed_[0-9]+_${ALGO}_complete" "${DEL[@]}" 2>/dev/null || true

# 3. Eval metric/metadata sidecars: run_id = <algo>_NNN, so basenames start
#    with '<algo>_' — a name pattern is prefix-anchored to the basename.
find "result/$TRACE/eval_runs/runs" -maxdepth 1 \
  -name "${ALGO}_[0-9][0-9][0-9]_*" "${DEL[@]}" 2>/dev/null || true

# 4. Snakemake per-job logs: (train|eval)_<seed>_<algo>.log, same anchoring.
find "logs/snakemake/$TRACE" -maxdepth 1 -regextype posix-extended \
  -regex ".*/(train|eval)_[0-9]+_${ALGO}\.log" "${DEL[@]}" 2>/dev/null || true

# 5. Manifest rows: drop this algo's rows (column 3 == algorithm, exact match)
#    so the retrain appends fresh rows instead of duplicating.
if [ -f "$MANIFEST" ]; then
  before=$(wc -l < "$MANIFEST")
  if [ "${DRYRUN:-0}" = 1 ]; then
    dropped=$(awk -F, -v a="$ALGO" 'NR>1 && $3==a' "$MANIFEST" | wc -l)
    echo "  [dry-run] would drop $dropped manifest row(s) from $MANIFEST"
  else
    awk -F, -v a="$ALGO" 'NR==1 || $3!=a' "$MANIFEST" > "$MANIFEST.tmp"
    mv "$MANIFEST.tmp" "$MANIFEST"
    echo "  manifest: $before -> $(wc -l < "$MANIFEST") lines"
  fi
fi

echo "Done. Now:  just run_full_slurm"
