#!/usr/bin/env python3
"""prune_manifest.py -- drop foreign-config rows from the run manifest.

Why this exists: smoke runs share logs/run_log.csv with production runs, and
they are NOT distinguishable by split_id. make_split.py builds split_id as
f"{trace}_r{ratio}" (make_split.py:84) and `just run_smoke <trace>` only
overrides seeds/algorithms/timesteps, so a smoke row carries the exact same
"deeplearn_job_r70" as the real thing. Filtering on split_id would therefore
drop everything or nothing.

What does separate them is the config that produced them: smoke trains
save_interval*total_saving = 200 timesteps with window 16 / tail 4, production
3000000 with window 512 / tail 64. Left in place, those rows reach
aggregate_results, which looks for a <run_id>_metrics.csv that evaluate_agents
never wrote (it loads the production checkpoint path) and dies under --strict.

Dry-run by default; --apply writes a timestamped backup first.

Usage:
    scripts/prune_manifest.py                        # show what would go
    scripts/prune_manifest.py --apply                # actually prune
    scripts/prune_manifest.py --split deeplearn_job_r70 --apply
    scripts/prune_manifest.py --split-prefix smoke_ --apply
"""

from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, default=Path("logs/run_log.csv"))
    # Defaults mirror config.yaml. Deliberately flags rather than a yaml read:
    # the nix python env ships no pyyaml.
    parser.add_argument("--window-size", type=int, default=512, help="window_size a production row must have.")
    parser.add_argument("--tail-size", type=int, default=64, help="tail_size a production row must have.")
    parser.add_argument(
        "--final-checkpoint", type=int, default=3_000_000,
        help="save_interval * total_saving; a production model_path ends in <this>.zip.",
    )
    parser.add_argument("--split", default=None, help="Only consider rows with this split_id.")
    parser.add_argument(
        "--split-prefix", default=None,
        help="Additionally drop rows whose split_id starts with this. Off by default: "
             "smoke runs reuse the production split_id, so this catches nothing unless "
             "a run was given a split of its own.",
    )
    parser.add_argument("--apply", action="store_true", help="Write the change (default: dry run).")
    parser.add_argument("--force", action="store_true", help="Allow a prune that empties the manifest.")
    return parser.parse_args()


def drop_reasons(row: pd.Series, args: argparse.Namespace) -> list[str]:
    """Why this row does not belong to the production grid. Empty list = keep."""
    reasons = []
    if args.split_prefix and str(row["split_id"]).startswith(args.split_prefix):
        reasons.append(f"split_id~{args.split_prefix}*")
    if pd.notna(row["window_size"]) and int(row["window_size"]) != args.window_size:
        reasons.append(f"window={row['window_size']}")
    if pd.notna(row["tail_size"]) and int(row["tail_size"]) != args.tail_size:
        reasons.append(f"tail={row['tail_size']}")
    # Baseline rows carry an empty model_path and have no checkpoint to check.
    model_path = str(row["model_path"]).strip()
    if model_path and model_path.lower() != "nan":
        expected = f"{args.final_checkpoint}.zip"
        if Path(model_path).name != expected:
            reasons.append(f"checkpoint={Path(model_path).name}")
    return reasons


def main() -> None:
    args = parse_args()
    if not args.manifest.exists():
        print(f"[ERROR] manifest not found: {args.manifest}")
        sys.exit(1)

    df = pd.read_csv(args.manifest)
    in_scope = df["split_id"].astype(str) == args.split if args.split else pd.Series(True, index=df.index)

    reasons = {idx: drop_reasons(df.loc[idx], args) for idx in df.index[in_scope]}
    doomed = [idx for idx, why in reasons.items() if why]

    print(f"{args.manifest}: {len(df)} row(s), {int(in_scope.sum())} in scope, {len(doomed)} to drop\n")
    if not doomed:
        print("Nothing to prune.")
        return

    for idx in doomed:
        row = df.loc[idx]
        print(f"  DROP {row['run_id']:<20} seed={str(row['seed']):<8} {row['split_id']:<20} {', '.join(reasons[idx])}")

    kept = df.drop(index=doomed)
    print(f"\nWould keep {len(kept)} row(s):")
    if not kept.empty:
        for algo, group in kept.groupby("algorithm"):
            ids = sorted(str(r) for r in group["run_id"])
            print(f"  {algo:<16} {len(group):>3}  {ids[0]} .. {ids[-1]}")

    if kept.empty and not args.force:
        print("\n[ERROR] that would empty the manifest. Check your --window-size/--tail-size/"
              "--final-checkpoint against the config that produced these runs, or pass --force.")
        sys.exit(1)

    if not args.apply:
        print("\nDry run. Re-run with --apply to write this.")
        return

    backup = args.manifest.with_suffix(f".csv.bak.{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(args.manifest, backup)
    kept.to_csv(args.manifest, index=False)
    print(f"\nBacked up to {backup}\nWrote {len(kept)} row(s) to {args.manifest}")


if __name__ == "__main__":
    main()
