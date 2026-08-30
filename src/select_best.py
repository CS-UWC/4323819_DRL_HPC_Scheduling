"""Select a Pareto-optimal treatment with pre-declared CI tie-breakers.

The selector does not use Nemenyi results to eliminate candidates. Nemenyi is
reported by the statistics stage; selection is deliberately limited to the
configured Pareto metrics and the configured Wilcoxon-CI tie-breakers so its
rationale matches the implemented decision rule.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from paretoset import paretoset

from src.utils import METRIC_DIRECTION, write_json

DEFAULT_PARETO_METRICS = ["avg_waiting", "avg_slowdown"]
DEFAULT_TIE_BREAKERS = ["avg_waiting", "avg_slowdown", "cpu_utilization"]
ALPHA = 0.05


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Select a Pareto-optimal treatment with CI tie-breakers."
    )
    parser.add_argument("--seed-summary", required=True, help="Path to seed_summary.csv")
    parser.add_argument("--ci", default=None, help="Path to confidence_intervals.csv")
    parser.add_argument(
        "--page-trend", default=None,
        help="Path to page_trend.csv (reported only; not used for selection)",
    )
    parser.add_argument(
        "--pareto-metrics", nargs="+", default=DEFAULT_PARETO_METRICS,
        help="Configured metrics for Pareto dominance.",
    )
    parser.add_argument(
        "--tie-breakers", nargs="+", default=DEFAULT_TIE_BREAKERS,
        help="Configured CI tie-breakers, applied in order.",
    )
    parser.add_argument("--output-dir", default="result")
    parser.add_argument("--alpha", type=float, default=ALPHA)
    return parser.parse_args()


def find_pareto_front(df: pd.DataFrame, metrics: list[str]) -> pd.DataFrame:
    sense = [
        "min" if METRIC_DIRECTION.get(metric, "lower_is_better") == "lower_is_better" else "max"
        for metric in metrics
    ]
    return df.loc[paretoset(df[metrics], sense=sense)].reset_index(drop=True)


def ci_lookup(ci_df: pd.DataFrame | None, metric: str, a: str, b: str) -> dict | None:
    if ci_df is None or ci_df.empty:
        return None
    subset = ci_df[ci_df["metric_name"] == metric]
    row = subset[(subset["treatment_a"] == a) & (subset["treatment_b"] == b)]
    if not row.empty:
        result = row.iloc[0]
        if pd.isna(result["ci_low"]) or pd.isna(result["ci_high"]):
            return None
        return {"ci_low": float(result["ci_low"]), "ci_high": float(result["ci_high"])}
    row = subset[(subset["treatment_a"] == b) & (subset["treatment_b"] == a)]
    if row.empty:
        return None
    result = row.iloc[0]
    if pd.isna(result["ci_low"]) or pd.isna(result["ci_high"]):
        return None
    return {"ci_low": -float(result["ci_high"]), "ci_high": -float(result["ci_low"])}


def is_significantly_better(
    ci_df: pd.DataFrame | None, metric: str, a: str, b: str, direction: str
) -> bool | None:
    """Return whether the CI for ``a - b`` proves that ``a`` is better."""
    ci = ci_lookup(ci_df, metric, a, b)
    if ci is None:
        return None
    return ci["ci_high"] < 0 if direction == "lower_is_better" else ci["ci_low"] > 0


def break_ties_with_cis(
    candidates: list[str], seed_summary: pd.DataFrame, ci_df: pd.DataFrame | None,
    tie_breakers: list[str],
) -> tuple[str, dict]:
    """Apply configured tie-breakers without treating missing CI evidence as proof."""
    means = seed_summary.groupby("treatment_id").mean(numeric_only=True)
    current = sorted(candidates)
    rationale: dict = {"initial_candidates": current.copy(), "steps": []}

    for metric in tie_breakers:
        if len(current) == 1:
            break
        if metric not in means.columns:
            rationale["steps"].append({"metric": metric, "skipped": "metric_missing"})
            continue
        direction = METRIC_DIRECTION.get(metric, "lower_is_better")
        values = means.loc[current, metric]
        best_value = values.min() if direction == "lower_is_better" else values.max()
        leaders = sorted(values[values == best_value].index.tolist())
        evidence = []
        survivors = set(current)
        for leader in leaders:
            for other in current:
                if other == leader:
                    continue
                significant = is_significantly_better(ci_df, metric, leader, other, direction)
                evidence.append({"leader": leader, "other": other, "significant": significant})
                if significant:
                    survivors.discard(other)
        current = sorted(survivors) if survivors else leaders
        rationale["steps"].append(
            {"metric": metric, "leaders_by_mean": leaders, "evidence": evidence,
             "survivors": current.copy()}
        )

    winner = current[0]
    if len(current) > 1:
        rationale["final_fallback"] = {
            "chosen": winner,
            "remaining": current,
            "rule": "lexical treatment_id after inconclusive configured CI tie-breakers",
        }
    return winner, rationale


def load_page_trend(path: Path, alpha: float) -> dict | None:
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path)
    except pd.errors.EmptyDataError:
        return None
    if df.empty:
        return None
    rows = df[["metric_name", "p_value"]].assign(significant=lambda data: data["p_value"] < alpha)
    return {"available": True, "rows": rows.to_dict("records"), "any_significant": bool(rows["significant"].any())}


def main() -> None:
    args = parse_args()
    pareto_metrics = list(args.pareto_metrics)
    tie_breakers = list(args.tie_breakers)
    seed_summary = pd.read_csv(args.seed_summary)
    seed_summary = seed_summary.rename(
        columns={column: column[:-5] for column in seed_summary.columns if column.endswith("_mean")}
    )
    required = list(dict.fromkeys([*pareto_metrics, *tie_breakers]))
    missing = [metric for metric in required if metric not in seed_summary.columns]
    if missing:
        print(f"[ERROR] seed_summary missing configured metrics: {missing}", file=sys.stderr)
        sys.exit(1)

    ci_df: pd.DataFrame | None = None
    if args.ci and Path(args.ci).exists():
        try:
            ci_df = pd.read_csv(args.ci)
        except pd.errors.EmptyDataError:
            ci_df = pd.DataFrame()
    elif args.ci:
        print(f"[WARN] CI path {args.ci} not found; tie-breaks will be inconclusive", file=sys.stderr)

    grouped_means = seed_summary.groupby("treatment_id").mean(numeric_only=True)
    pareto_df = find_pareto_front(grouped_means[pareto_metrics].reset_index(), pareto_metrics)
    candidates = sorted(pareto_df["treatment_id"].astype(str).tolist())
    if not candidates:
        raise ValueError("No Pareto candidates found")
    if len(candidates) == 1:
        winner, final_rationale = candidates[0], {"method": "single_pareto_candidate"}
    else:
        winner, details = break_ties_with_cis(candidates, seed_summary, ci_df, tie_breakers)
        final_rationale = {"method": "configured_ci_tie_breakers", "details": details}

    best_algorithm = {
        "treatment_id": winner,
        "selection_rationale": {
            "method": "pareto_front_plus_configured_ci_tie_breakers",
            "pareto_metrics": pareto_metrics,
            "tie_breakers": tie_breakers,
            "pareto_front": candidates,
            "page_trend": load_page_trend(Path(args.page_trend), args.alpha) if args.page_trend else None,
            "final_rationale": final_rationale,
        },
        "tie_break_metrics": {
            metric: float(grouped_means.loc[winner, metric]) for metric in tie_breakers
        },
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "best_algorithm.json"
    write_json(best_algorithm, output_path)
    print(f"[OK] winner={winner} -> wrote {output_path}")


if __name__ == "__main__":
    main()
