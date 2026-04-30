""" aggregate_results.py
Aggregates evaluation outputs from evaluate_agents.py into:
  - eval_long.csv          : per-run normalised long-format table
  - seed_summary.csv       : per-seed aggregation (mean/std per metric)
  - algorithm_summary.csv  : algorithm-level aggregation across seeds
  - aggregate_metadata.json: reproducibility sidecar

References:
  - pandas read_csv:     https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
  - pandas groupby:      https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html
  - pandas concat:       https://pandas.pydata.org/docs/reference/api/pandas.concat.html
  - argparse:            https://docs.python.org/3/library/argparse.html
  - pathlib:             https://docs.python.org/3/library/pathlib.html
  - json:                https://docs.python.org/3/library/json.html
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from numpy._core.numeric import dtype
import pandas as pd
from pandas.io.api import read_csv

# ---------------------------------------------------------------------------
# Schema constants
# ---------------------------------------------------------------------------

MANIFEST_REQUIRED = [
    "run_id", "algorithm", "use_masking", "seed",
    "split_id", "model_path", "trace_file", "topology_file", "node_file",
]

EVAL_REQUIRED = [
    "run_id", "algorithm", "use_masking", "seed", "split_id",
    "episode_reward", "decision_count",
    "max_waiting", "avg_waiting",
    "max_slowdown", "avg_slowdown",
    "avg_turnaround",
    "cpu_utilization", "gpu_utilization",
]

# Metrics that must be finite (non-NaN, non-inf) in every row
CORE_METRICS = [
    "episode_reward",
    "max_waiting", "avg_waiting",
    "max_slowdown", "avg_slowdown",
    "avg_turnaround",
    "cpu_utilization", "gpu_utilization",
    "decision_count",
    "decision_latency_mean_ms",
    "eval_wall_s",
]

# Grouping keys for aggregation
GROUP_KEYS = ["algorithm", "use_masking", "seed", "split_id"]
ALGO_KEYS  = ["algorithm", "use_masking", "split_id"]


# ---------------------------------------------------------------------------
# CLI
# Ref: https://docs.python.org/3/library/argparse.html
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    """
    Parse CLI arguments.

    Expected usage:
        python aggregate_results.py \\
            --manifest logs/run_log.csv \\
            --eval-root result/eval_runs/runs \\
            --output-dir result/aggregate
    """
    parser = argparse.ArgumentParser(description="Aggregate RL evaluation outputs.")
    parser.add_argument("--manifest",   required=True,                   type=str, help="Path to run manifest CSV.")
    parser.add_argument("--eval-root",  default="result/eval_runs/runs", type=str, help="Directory containing per-run eval CSVs.")
    parser.add_argument("--output-dir", default="result/aggregate",      type=str, help="Directory to write aggregated outputs.")
    parser.add_argument("--strict",     action=argparse.BooleanOptionalAction, default=True, help="Fail if any expected eval file is missing.")
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Manifest loading and validation
# Ref: https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
# ---------------------------------------------------------------------------

def _parse_bool(value: str) -> bool:
    """
    Parse a string representation of a boolean.
    Ref: reused from evaluate_agents.py for consistency.
    """
    v = str(value).strip().lower()
    if v in {"1", "true", "t", "yes", "y"}:
        return True
    if v in {"0", "false", "f", "no", "n"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def load_manifest(manifest_path: Path) -> pd.DataFrame:
    """
    Ref: https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
    Ref: https://pandas.pydata.org/docs/user_guide/missing_data.html (nullable int)
    """
    df = read_csv(manifest_path, dtype=str, skipinitialspace=True)
    df["use_masking"] = df["use_masking"].apply(_parse_bool)
    df["seed"] = df["seed"].astype("Int64")

    return df


def validate_manifest_schema(df: pd.DataFrame) -> None:
    """
    Validate the manifest DataFrame:
      - All MANIFEST_REQUIRED columns are present.
      - No duplicate run_id values.

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.duplicated.html
    """
    # TODO: check all MANIFEST_REQUIRED columns are present, raise ValueError listing missing ones
    # TODO: check for duplicate run_id values and raise if found
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Eval artifact discovery
# Ref: https://docs.python.org/3/library/pathlib.html
# ---------------------------------------------------------------------------

def discover_eval_artifacts(
    manifest_df: pd.DataFrame,
    eval_root: Path,
    strict: bool,
) -> dict[str, Path]:
    """
    For each run_id in the manifest, resolve the expected eval CSV path.
    Expected filename pattern: <run_id>_metrics.csv

    In strict mode, raise FileNotFoundError if any file is missing.
    In non-strict mode, warn and skip missing files.

    Returns a dict mapping run_id -> Path for all found files.

    Ref: https://docs.python.org/3/library/pathlib.html#pathlib.Path.exists
    """
    # TODO: iterate manifest run_ids
    # TODO: build expected path: eval_root / f"{run_id}_metrics.csv"
    # TODO: if missing and strict=True, raise FileNotFoundError
    # TODO: if missing and strict=False, print warning and skip
    # TODO: return dict of {run_id: path} for found files
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Eval CSV loading and validation
# Ref: https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
# ---------------------------------------------------------------------------

def load_eval_csv(path: Path) -> pd.DataFrame:
    """
    Read one evaluation CSV with explicit dtype mapping.

    Define string dtypes for ID columns and float for metric columns
    so pandas never silently misinterprets a value.

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.read_csv.html
    """
    # TODO: define dtype map — string for ID cols, float for metric cols
    # TODO: read CSV with that dtype map
    # TODO: return DataFrame
    raise NotImplementedError


def validate_eval_schema(df: pd.DataFrame, run_id: str) -> None:
    """
    Validate a single eval DataFrame:
      - All EVAL_REQUIRED columns are present.
      - CORE_METRICS columns are numeric.
      - No NaN or inf values in CORE_METRICS columns.

    Raise ValueError with run_id context if any check fails.

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.isnull.html
    Ref: https://numpy.org/doc/stable/reference/generated/numpy.isfinite.html
    """
    # TODO: check EVAL_REQUIRED columns are present
    # TODO: for each CORE_METRICS column, check dtype is numeric (pd.api.types.is_numeric_dtype)
    # TODO: check no NaN values in CORE_METRICS columns
    # TODO: check no inf values using np.isfinite
    # TODO: raise ValueError with run_id context if any check fails
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Metadata attachment
# ---------------------------------------------------------------------------

def attach_manifest_metadata(eval_df: pd.DataFrame, manifest_row: pd.Series) -> pd.DataFrame:
    """
    Overwrite ID/metadata columns on the eval DataFrame with canonical
    values from the manifest row. This ensures consistency even if the
    eval CSV has slightly different formatting (e.g. use_masking casing).

    Canonical columns: run_id, algorithm, use_masking, seed, split_id.

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.assign.html
    """
    # TODO: use df.assign() to overwrite the five canonical ID columns from manifest_row
    # TODO: return the updated DataFrame
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Wide table construction
# Ref: https://pandas.pydata.org/docs/reference/api/pandas.concat.html
# ---------------------------------------------------------------------------

def build_eval_wide(eval_frames: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Concatenate all per-run eval DataFrames into a single wide-format table.
    Reset the index so it is contiguous (0, 1, 2, ...).

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.concat.html
    """
    # TODO: pd.concat the list of frames with ignore_index=True
    # TODO: return the combined DataFrame
    raise NotImplementedError


def check_key_uniqueness(df: pd.DataFrame, key_cols: list[str], context: str) -> None:
    """
    Verify there are no duplicate rows at the granularity defined by key_cols.
    Raise ValueError with a context label and the offending rows if duplicates found.

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.duplicated.html
    """
    # TODO: df.duplicated(subset=key_cols, keep=False) to find all duplicate rows
    # TODO: if any found, raise ValueError showing context and the duplicate rows
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Aggregation
# Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html
# Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.agg.html
# ---------------------------------------------------------------------------

def aggregate_seed_summary(eval_long: pd.DataFrame) -> pd.DataFrame:
    """
    Group by GROUP_KEYS (algorithm, use_masking, seed, split_id) and compute
    mean and std for each metric in CORE_METRICS.

    This gives one row per (algorithm, seed) combination — useful for checking
    variance within a seed before aggregating across seeds.

    Column naming convention: <metric>_mean, <metric>_std

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html
    Ref: https://pandas.pydata.org/docs/reference/api/pandas.core.groupby.DataFrameGroupBy.agg.html
    """
    # TODO: filter df to GROUP_KEYS + CORE_METRICS columns only
    # TODO: groupby(GROUP_KEYS) and agg(["mean", "std"])
    # TODO: flatten MultiIndex columns: ("episode_reward", "mean") -> "episode_reward_mean"
    # TODO: reset_index() so GROUP_KEYS become regular columns
    # TODO: return summary DataFrame
    raise NotImplementedError


def aggregate_algorithm_summary(seed_summary: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate across seeds by grouping on ALGO_KEYS (algorithm, use_masking, split_id).
    Compute mean and std of the per-seed means for each metric.

    This gives the final algorithm-level summary table. The std here reflects
    variance across seeds — the key input for statistical analysis.

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html
    """
    # TODO: identify the "_mean" columns from seed_summary (these are what you aggregate)
    # TODO: groupby(ALGO_KEYS) and agg those columns with ["mean", "std"]
    # TODO: flatten MultiIndex columns
    # TODO: reset_index and return
    raise NotImplementedError


# ---------------------------------------------------------------------------
# QC
# ---------------------------------------------------------------------------

def compute_aggregation_qc(
    eval_long: pd.DataFrame,
    seed_summary: pd.DataFrame,
    algo_summary: pd.DataFrame,
) -> dict[str, Any]:
    """
    Produce QC stats across all three tables:
      - Row counts per table
      - NaN counts per column in eval_long
      - Duplicate key counts in eval_long
      - Min/max/mean for each core metric in eval_long

    Returns a dict suitable for embedding in the metadata JSON.

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.describe.html
    Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.isnull.html
    """
    # TODO: collect row counts for all three DataFrames
    # TODO: NaN counts per column for eval_long: df.isnull().sum().to_dict()
    # TODO: duplicate count on ["run_id"] in eval_long
    # TODO: describe() stats for CORE_METRICS columns, convert to dict
    # TODO: return all as a nested dict
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Metadata sidecar
# ---------------------------------------------------------------------------

def _git_hash() -> str | None:
    """Return the current git commit hash, or None if not in a git repo."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return None


def _file_sha256(path: Path) -> str:
    """
    Return the SHA-256 hex digest of a file.
    Used to fingerprint the manifest so results are traceable to an exact input.

    Ref: https://docs.python.org/3/library/hashlib.html
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def build_aggregate_metadata(
    args: argparse.Namespace,
    manifest_df: pd.DataFrame,
    qc_stats: dict[str, Any],
) -> dict[str, Any]:
    """
    Build the reproducibility sidecar dict containing:
      - timestamp_utc   : when aggregation was run
      - command         : full sys.argv invocation
      - git_hash        : current commit (if available)
      - manifest_sha256 : fingerprint of the manifest file
      - split_ids       : unique split IDs present in the manifest
      - algorithms      : unique algorithms present in the manifest
      - qc_stats        : output of compute_aggregation_qc

    Ref: https://docs.python.org/3/library/sys.html#sys.argv
    Ref: https://docs.python.org/3/library/hashlib.html
    """
    # TODO: datetime.now(timezone.utc).isoformat() for timestamp
    # TODO: " ".join(sys.argv) for command
    # TODO: _git_hash()
    # TODO: _file_sha256(Path(args.manifest))
    # TODO: manifest_df["split_id"].unique().tolist() for split_ids
    # TODO: manifest_df["algorithm"].unique().tolist() for algorithms
    # TODO: embed qc_stats
    # TODO: return as dict
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Output writers
# Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html
# ---------------------------------------------------------------------------

def write_csv(df: pd.DataFrame, path: Path) -> None:
    """
    Write a DataFrame to CSV with deterministic formatting.
      - index=False      : row numbers carry no meaning
      - float_format     : consistent 6dp float representation

    Ref: https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.to_csv.html
    """
    # TODO: path.parent.mkdir(parents=True, exist_ok=True)
    # TODO: df.to_csv(path, index=False, float_format="%.6f")
    raise NotImplementedError


def write_json(obj: dict[str, Any], path: Path) -> None:
    """
    Write a dict to JSON with deterministic formatting.
      - indent=2        : human readable
      - sort_keys=True  : deterministic diffs across runs

    Ref: https://docs.python.org/3/library/json.html
    """
    # TODO: path.parent.mkdir(parents=True, exist_ok=True)
    # TODO: open path and json.dump with indent=2, sort_keys=True
    raise NotImplementedError


# ---------------------------------------------------------------------------
# Main orchestration
# ---------------------------------------------------------------------------

def main() -> None:
    """
    Full aggregation pipeline:
      1.  Parse args
      2.  Load and validate manifest
      3.  Discover eval artifacts
      4.  Load, validate, and attach metadata to each eval CSV
      5.  Build long table and check key uniqueness
      6.  Aggregate to seed and algorithm summaries
      7.  Compute QC stats
      8.  Build and write metadata sidecar
      9.  Write all CSVs
      10. Exit non-zero if any contract violations occurred
    """
    args = parse_args()
    manifest_path = Path(args.manifest)
    eval_root     = Path(args.eval_root)
    output_dir    = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # --- 1. Manifest ---
    manifest_df = load_manifest(manifest_path)
    validate_manifest_schema(manifest_df)

    # --- 2. Discover artifacts ---
    artifact_paths = discover_eval_artifacts(manifest_df, eval_root, strict=args.strict)

    # --- 3. Load and validate each eval CSV ---
    eval_frames: list[pd.DataFrame] = []
    failures: list[str] = []

    for run_id, csv_path in artifact_paths.items():
        try:
            df = load_eval_csv(csv_path)
            validate_eval_schema(df, run_id)
            manifest_row = manifest_df[manifest_df["run_id"] == run_id].iloc[0]
            df = attach_manifest_metadata(df, manifest_row)
            eval_frames.append(df)
        except Exception as e:
            failures.append(f"{run_id}: {e}")
            print(f"[FAIL] {run_id} :: {e}")

    if failures and args.strict:
        print(f"\n{len(failures)} run(s) failed validation. Exiting.")
        sys.exit(1)

    if not eval_frames:
        print("No valid eval frames to aggregate. Exiting.")
        sys.exit(1)

    # --- 4. Build long table ---
    eval_long = build_eval_wide(eval_frames)
    check_key_uniqueness(eval_long, ["run_id"], context="eval_long")

    # --- 5. Aggregate ---
    seed_summary = aggregate_seed_summary(eval_long)
    algo_summary = aggregate_algorithm_summary(seed_summary)

    # --- 6. QC + metadata ---
    qc_stats = compute_aggregation_qc(eval_long, seed_summary, algo_summary)
    metadata  = build_aggregate_metadata(args, manifest_df, qc_stats)

    # --- 7. Write outputs ---
    write_csv(eval_long,    output_dir / "eval_long.csv")
    write_csv(seed_summary, output_dir / "seed_summary.csv")
    write_csv(algo_summary, output_dir / "algorithm_summary.csv")
    write_json(metadata,    output_dir / "aggregate_metadata.json")

    print(f"\nDone. Outputs written to {output_dir}/")
    print(f"  Runs aggregated : {len(eval_frames)}")
    print(f"  Runs failed     : {len(failures)}")

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
