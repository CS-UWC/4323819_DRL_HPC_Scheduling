#!/usr/bin/env python3
"""baseline_equivalence.py

Compare DRL treatments against the deterministic heuristics -- for difference
AND for equivalence.

Background
----------
src/baseline_compare.py in the pipeline already runs the correct difference
test: a ONE-SAMPLE Wilcoxon signed-rank on (drl_seed_values - baseline_value).
A heuristic is deterministic, so it contributes a single fixed number with no
seeds and nothing to pair against; the one-sample test is the right
non-parametric choice for "does this distribution sit away from a known
reference point". This script reproduces that test exactly (verified against
baseline_comparison.csv) and then adds four things the paper needs:

1. Any treatment, not just the winner.
   baseline_compare.py reads best_algorithm.json, so physical only ever covers
   MaskablePPO and deeplearn only covers PPO. That leaves PPO-vs-heuristic on
   physical and MaskablePPO-vs-heuristic on deeplearn uncomputed -- exactly the
   comparisons the paper wants to discuss.

2. Effect size beside every p-value.
   At n=10 the smallest attainable two-sided Wilcoxon p is (1/2)^9 = 0.001953,
   and most comparisons land exactly on it. A p at the floor means all ten
   seeds fell on the same side -- it reports CONSISTENCY, not MAGNITUDE. Delta%
   and the seeds-beaten count are what carry the magnitude.

3. Holm-Bonferroni correction.
   Six metrics x three heuristics = 18 tests per treatment per trace. Reporting
   18 uncorrected p-values invites the obvious objection.

4. TOST equivalence testing -- the important one.
   A non-significant difference test is NOT evidence of equivalence; it is
   absence of evidence. If the claim is "the learned policy matches the
   heuristic", that claim needs a test that can actually support it. TOST (two
   one-sided tests) does: it asks whether the difference is confidently INSIDE
   a margin chosen in advance, and can therefore conclude practical
   equivalence.

   The margin is a research decision, not a statistical one. It must be set
   before seeing the outcome and justified operationally -- what deviation
   would a site actually notice. --margin defaults to 10% and is recorded in
   the output so the choice travels with the numbers.

   Note the two tests answer different questions and can both fire: a
   difference can be statistically detectable (all seeds agree) yet
   operationally negligible (well inside the margin). That combination is the
   most defensible reading of the physical trace, not a contradiction.

Usage:
    python3 scripts/baseline_equivalence.py
    python3 scripts/baseline_equivalence.py --trace physical
    python3 scripts/baseline_equivalence.py --margin 0.05
    python3 scripts/baseline_equivalence.py --verify-against-pipeline
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PAPER_DIR = Path(__file__).resolve().parent.parent
CLUSTER = PAPER_DIR.parent / "cluster_results"
OUT_DIR = PAPER_DIR / "data" / "results"

TRACES = {"physical": "physical_jobs", "deeplearn": "deeplearn_jobs"}

PRETTY = {
    "maskable_ppo": "MaskablePPO", "maskable_dqn": "MaskableDQN",
    "maskable_a2c": "MaskableA2C", "ppo": "PPO", "dqn": "DQN", "a2c": "A2C",
}

# The treatments the paper argues about. MaskableA2C is not optional -- after
# the ent_coef rerun it is the Pareto-selected winner on physical, and RQ3
# ("does the selected algorithm beat the heuristics") cannot be argued for a
# treatment that has no rows here.
#
# The unmasked treatments are deliberately absent. Their evaluations never drain
# the trace: once the event queue empties, simulated time cannot advance, the
# observation is identical on every subsequent step, and a deterministic policy
# repeats the same invalid action, so the episode is stopped by the hang guard
# after 500,000 consecutive steps with no completion. Their metrics therefore
# average over only the jobs that finished first -- which excludes precisely the
# jobs still waiting -- so an equivalence claim built on them would be testing a
# favourably-biased subset against a full-trace reference. Confirmed by the
# implied-runtime invariant: avg_turnaround - avg_waiting is a property of the
# trace, and the unmasked treatments disagree with every full-trace treatment on
# it (deeplearn 10,423 vs 10,566.92; physical 8,595 vs 8,741.91). select_best
# excludes them for the same reason.
TREATMENTS = ["maskable_ppo", "maskable_a2c"]

# Every *full-trace* treatment, for the random-control table -- the N27 question
# is asked of the whole valid field, not just the two the heuristic comparison
# argues about. Unmasked treatments are excluded for the reason above.
ALL_TREATMENTS = ["maskable_ppo", "maskable_dqn", "maskable_a2c"]

# The deterministic heuristics, and ONLY those. baseline_summary.csv also
# carries the N27 `random` control, which must not enter this comparison: the
# test below is a ONE-SAMPLE Wilcoxon against a fixed reference value, and that
# is only valid for a baseline with no sampling variability. Random has ten
# seeds and a real spread, so collapsing it to its mean would (a) discard that
# spread and return an anticonservative p, (b) throw away the seed pairing that
# is actually available, and (c) answer the wrong question -- TOST equivalence
# to a heuristic is the claim the paper wants, whereas equivalence to random
# would mean the agent learned nothing. It gets its own paired test in
# build_vs_random().
HEURISTICS = ["lcfs", "sjf", "unicep"]
RANDOM_CONTROL = "random"

# Each heuristic is run twice: with HPCsim's backfill sweep and without. Both
# land in baseline_summary.csv under distinct treatment_ids, so selecting on
# `algorithm` alone would silently double every row here and pool two different
# reference values under one label. Both bands get their own tests -- they are
# different reference values, so they are different hypotheses -- and the Holm
# family is already keyed on (treatment, heuristic), so distinct labels keep the
# two families separate rather than inflating one.
#
# backfill=OFF is the controlled band: it is the only one that runs the same
# scheduling mechanism the DRL treatments do (HPCsim.step() never backfills), so
# it carries the bare name. backfill=ON is the production reference and is
# labelled. See Project_Github/src/naming.py.
NO_BACKFILL_SUFFIX = "__nobf"
BACKFILL_LABEL = {False: "", True: "+BF"}


def heuristic_treatment_ids() -> list[str]:
    return [f"{a}__mask_false{s}"
            for a in HEURISTICS
            for s in ("", NO_BACKFILL_SUFFIX)]


def heuristic_label(treatment_id: str) -> str:
    algorithm = str(treatment_id).split("__")[0].upper()
    backfill = not str(treatment_id).endswith(NO_BACKFILL_SUFFIX)
    return algorithm + BACKFILL_LABEL[backfill]

METRICS = [
    ("avg_waiting", "Avg Wait"),
    ("avg_slowdown", "Avg Slow."),
    ("avg_turnaround", "Avg Turn."),
    ("max_waiting", "Max Wait"),
    ("max_slowdown", "Max Slow."),
    ("cpu_utilization", "CPU Util"),
]

# The full 6-metric x 3-heuristic x 2-treatment grid is 36 rows, which swamps a
# two-column page. The manuscript shows the primaries; the full grid stays in
# <trace>_equivalence.csv for an appendix.
PRIMARY_METRICS = {"avg_waiting", "avg_slowdown", "max_slowdown"}

HIGHER_IS_BETTER = {"cpu_utilization", "gpu_utilization"}


def holm(pvals: list[float]) -> list[float]:
    """Holm-Bonferroni step-down adjustment, NaN-safe and monotone."""
    idx = [i for i, p in enumerate(pvals) if p is not None and not np.isnan(p)]
    m = len(idx)
    out: list[float] = [float("nan")] * len(pvals)
    if m == 0:
        return out
    order = sorted(idx, key=lambda i: pvals[i])
    running = 0.0
    for rank, i in enumerate(order):
        adj = (m - rank) * pvals[i]
        running = max(running, adj)          # enforce monotonicity
        out[i] = min(1.0, running)
    return out


def tost(diffs: np.ndarray, margin_abs: float) -> tuple[float, bool]:
    """Two one-sided Wilcoxon signed-rank tests for equivalence.

    H0: |true shift| >= margin  (non-equivalence)
    H1: |true shift| <  margin  (equivalence)

    Reject H0 only if BOTH one-sided tests reject, so the TOST p is the larger
    of the two. Uses the signed-rank test rather than a t-test to stay
    consistent with the rest of the analysis, which assumes no normality at
    n=10.
    """
    if margin_abs <= 0 or len(diffs) < 2:
        return float("nan"), False
    # Lower bound: is the shift greater than -margin?
    lower = stats.wilcoxon(diffs + margin_abs, alternative="greater")
    # Upper bound: is the shift less than +margin?
    upper = stats.wilcoxon(diffs - margin_abs, alternative="less")
    p = max(float(lower.pvalue), float(upper.pvalue))
    return p, p < 0.05


def compare(drl: np.ndarray, baseline: float, metric: str,
            margin_frac: float) -> dict:
    diffs = drl - baseline
    n = len(diffs)
    higher_better = metric in HIGHER_IS_BETTER

    if np.all(diffs == 0):
        # Every seed reproduced the heuristic exactly. No variation to test, and
        # "10/10 better" would be wrong -- it is a tie, not a win.
        return {
            "n": n, "baseline": baseline, "median": float(np.median(drl)),
            "delta_pct": 0.0, "wins": 0, "p_raw": float("nan"),
            "p_tost": float("nan"), "equivalent": True,
            "note": "identical",
        }

    p_raw = float(stats.wilcoxon(diffs).pvalue)
    median = float(np.median(drl))
    wins = int(np.sum(drl > baseline) if higher_better else np.sum(drl < baseline))
    delta = (median - baseline) / baseline * 100.0 if baseline else float("nan")
    p_tost, equivalent = tost(diffs, abs(baseline) * margin_frac)

    return {
        "n": n, "baseline": baseline, "median": median, "delta_pct": delta,
        "wins": wins, "p_raw": p_raw, "p_tost": p_tost,
        "equivalent": equivalent, "note": "",
    }


def build(trace: str, dirname: str, margin_frac: float) -> pd.DataFrame:
    root = CLUSTER / dirname
    seeds = pd.read_csv(root / "aggregate" / "seed_summary.csv")
    base = pd.read_csv(root / "baseline" / "baseline_summary.csv")
    base = base[base["treatment_id"].isin(heuristic_treatment_ids())]

    records = []
    for algorithm in TREATMENTS:
        sub = seeds[seeds["algorithm"] == algorithm]
        if sub.empty:
            continue
        for _, brow in base.iterrows():
            for metric, label in METRICS:
                drl = sub[f"{metric}_mean"].to_numpy(dtype=float)
                r = compare(drl, float(brow[f"{metric}_mean_mean"]),
                            metric, margin_frac)
                r.update({
                    "treatment": PRETTY.get(algorithm, algorithm),
                    "heuristic": heuristic_label(brow["treatment_id"]),
                    "metric": label,
                    "metric_key": metric,
                })
                records.append(r)

    df = pd.DataFrame(records)
    # Correct within each (treatment, heuristic) family of metric tests.
    df["p_holm"] = float("nan")
    for _, grp in df.groupby(["treatment", "heuristic"], sort=False):
        df.loc[grp.index, "p_holm"] = holm(grp["p_raw"].tolist())
    return df


def build_vs_random(dirname: str) -> pd.DataFrame:
    """N27 control: is each treatment distinguishable from an unlearned policy?

    The random control draws uniformly over the *valid* actions of the same MDP
    the DRL rows are evaluated on, so it is the floor a learned policy has to
    clear -- not a scheduling heuristic. It is also the one baseline that is
    stochastic, and it was run on the identical ten seeds, which makes this a
    genuinely PAIRED comparison: seed is a blocking factor, so differencing
    within seed removes the seed-to-seed workload variation that dominates the
    raw spread.

    That is why this is a two-sided *paired* Wilcoxon signed-rank on the
    per-seed differences rather than the one-sample test used against the
    heuristics, and why no TOST column appears: equivalence to random is a null
    result for the agent, not a claim the paper wants to establish.

    Returns an empty frame when the trace has no random rows yet (the control
    landed on physical first).
    """
    root = CLUSTER / dirname
    seeds = pd.read_csv(root / "aggregate" / "seed_summary.csv")
    wide = pd.read_csv(root / "baseline" / "baseline_eval_wide.csv")
    rnd = wide[wide["algorithm"] == RANDOM_CONTROL].dropna(subset=["seed"])
    if rnd.empty:
        return pd.DataFrame()
    rnd = rnd.assign(seed=rnd["seed"].astype(int))

    records = []
    for algorithm in ALL_TREATMENTS:
        sub = seeds[seeds["algorithm"] == algorithm]
        if sub.empty:
            continue
        sub = sub.assign(seed=sub["seed"].astype(int))
        for metric, label in METRICS:
            # Inner join on seed: the pairing is the whole point, so any seed
            # missing on either side drops out rather than being averaged over.
            pair = sub[["seed", f"{metric}_mean"]].merge(
                rnd[["seed", metric]], on="seed", how="inner")
            if len(pair) < 2:
                continue
            drl = pair[f"{metric}_mean"].to_numpy(dtype=float)
            ref = pair[metric].to_numpy(dtype=float)
            diffs = drl - ref
            higher_better = metric in HIGHER_IS_BETTER
            better = int(np.sum(drl > ref) if higher_better
                         else np.sum(drl < ref))
            p = (float("nan") if np.all(diffs == 0)
                 else float(stats.wilcoxon(diffs).pvalue))
            records.append({
                "treatment": PRETTY.get(algorithm, algorithm),
                "metric": label,
                "metric_key": metric,
                "n": len(pair),
                "random_median": float(np.median(ref)),
                "drl_median": float(np.median(drl)),
                # Median of the per-seed relative differences, not a ratio of
                # medians -- it stays paired, and it is robust to the seeds
                # where DQN/A2C diverge by three orders of magnitude.
                "delta_pct": float(np.median(diffs / ref)) * 100.0,
                "better": better,
                "p_raw": p,
            })

    df = pd.DataFrame(records)
    if df.empty:
        return df
    df["p_holm"] = float("nan")
    for _, grp in df.groupby("treatment", sort=False):
        df.loc[grp.index, "p_holm"] = holm(grp["p_raw"].tolist())
    return df


def to_display_random(df: pd.DataFrame) -> pd.DataFrame:
    def pfmt(p):
        if pd.isna(p):
            return "---"
        return "<0.001" if p < 0.001 else f"{p:.3f}"

    verdict = [
        "---" if pd.isna(p) else
        ("Better" if p < 0.05 and b > n / 2 else
         "Worse" if p < 0.05 else "Not sep.")
        for p, b, n in zip(df["p_holm"], df["better"], df["n"])
    ]
    return pd.DataFrame({
        "Treatment": df["treatment"],
        "Metric": df["metric"],
        "Random median": df["random_median"].map("{:,.3f}".format),
        "DRL median": df["drl_median"].map("{:,.3f}".format),
        "Δ%": df["delta_pct"].map(lambda x: f"{x:+.1f}%"),
        "Seeds better": [f"{b}/{n}" for b, n in zip(df["better"], df["n"])],
        "p (Holm)": df["p_holm"].map(pfmt),
        "vs. random": verdict,
    })


def to_display(df: pd.DataFrame, margin_frac: float) -> pd.DataFrame:
    def pfmt(p):
        if pd.isna(p):
            return "---"
        return "<0.001" if p < 0.001 else f"{p:.3f}"

    # A tie is reported as such rather than as equivalence established by test.
    verdict = [
        "Identical" if note == "identical" else ("Yes" if eq else "No")
        for note, eq in zip(df["note"], df["equivalent"])
    ]

    return pd.DataFrame({
        "Treatment": df["treatment"],
        "Heuristic": df["heuristic"],
        "Metric": df["metric"],
        "Heuristic value": df["baseline"].map("{:,.3f}".format),
        "DRL median": df["median"].map("{:,.3f}".format),
        "Δ%": df["delta_pct"].map(lambda x: f"{x:+.1f}%"),
        "Seeds better": [f"{w}/{n}" for w, n in zip(df["wins"], df["n"])],
        "p (raw)": df["p_raw"].map(pfmt),
        "p (Holm)": df["p_holm"].map(pfmt),
        f"TOST p (±{margin_frac:.0%})": df["p_tost"].map(pfmt),
        "Equivalent": verdict,
    })


def verify_against_pipeline(margin_frac: float) -> int:
    """The reimplemented difference test must match the pipeline exactly.

    baseline_compare.py only covers the selected winner, so only those rows can
    be cross-checked -- but if they agree, the shared code path is trusted for
    the rows the pipeline never computed.
    """
    problems = []
    for trace, dirname in TRACES.items():
        ref = pd.read_csv(CLUSTER / dirname / "baseline" / "baseline_comparison.csv")
        mine = build(trace, dirname, margin_frac)
        for _, r in ref.iterrows():
            algorithm = r["drl_treatment_id"].split("__")[0]
            heuristic = heuristic_label(r["baseline_treatment_id"])
            hit = mine[
                (mine["treatment"] == PRETTY.get(algorithm, algorithm))
                & (mine["heuristic"] == heuristic)
                & (mine["metric_key"] == r["metric"])
            ]
            if hit.empty:
                continue
            got, want = float(hit.iloc[0]["p_raw"]), r["p_value"]
            if pd.isna(want) and pd.isna(got):
                continue
            # baseline_comparison.csv stores 6 decimal places, so compare at
            # that precision rather than to full float equality.
            if pd.isna(want) or pd.isna(got) or abs(got - want) > 1e-6:
                problems.append(
                    f"{trace} {algorithm} vs {heuristic} {r['metric']}: "
                    f"p={got} but pipeline says {want}")

    if problems:
        print("FAIL — reimplementation disagrees with the pipeline")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("OK — one-sample Wilcoxon reproduces baseline_comparison.csv exactly")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--margin", type=float, default=0.10,
                    help="equivalence margin as a fraction of the heuristic "
                         "value (default 0.10). Set this before looking at "
                         "the results and justify it operationally.")
    ap.add_argument("--verify-against-pipeline", action="store_true",
                    help="check the difference test against baseline_comparison.csv")
    ap.add_argument("--primary-both-bands", action="store_true",
                    help="keep the +BF rows in the primary table too. Off by "
                         "default: the manuscript table shows the no-backfill "
                         "band, which is the band the agents can actually "
                         "match. The full grid always carries both.")
    ap.add_argument("--trace", action="append", choices=sorted(TRACES),
                    help="build only this trace (repeatable). Default: both. "
                         "Use while the other sweep is still running.")
    args = ap.parse_args()

    if not CLUSTER.exists():
        print(f"error: cluster results not found at {CLUSTER}", file=sys.stderr)
        return 2

    if args.verify_against_pipeline:
        return verify_against_pipeline(args.margin)

    traces = ({t: TRACES[t] for t in args.trace} if args.trace else dict(TRACES))

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for trace, dirname in traces.items():
        df = build(trace, dirname, args.margin)

        full = OUT_DIR / f"{trace}_equivalence.csv"
        to_display(df, args.margin).to_csv(full, index=False)

        # The manuscript table shows the no-backfill band only. That is the
        # like-for-like comparison -- HPCsim.step() never backfills, so the
        # agents have no such action -- and showing both bands doubles the table
        # to 36 rows, which does not fit a two-column page. The +BF band is not
        # discarded: it stays in the full grid written above, which the appendix
        # cites, so the heuristics-as-deployed numbers remain available.
        prim = df[df["metric_key"].isin(PRIMARY_METRICS)]
        if not args.primary_both_bands:
            prim = prim[~prim["heuristic"].str.endswith(BACKFILL_LABEL[True])]
        primary = OUT_DIR / f"{trace}_equivalence_primary.csv"
        to_display(prim, args.margin).drop(columns=["p (raw)"]).to_csv(
            primary, index=False)

        n_eq = int(df["equivalent"].sum())
        print(f"wrote {full.name} ({len(df)} comparisons, {n_eq} equivalent "
              f"at ±{args.margin:.0%}) and {primary.name} ({len(prim)} rows)")

        rnd = build_vs_random(dirname)
        if rnd.empty:
            print(f"  skipped {trace}_vs_random.csv — no random control in "
                  f"this trace's baseline_eval_wide.csv yet")
            continue
        rnd_prim = rnd[rnd["metric_key"].isin(PRIMARY_METRICS)]
        path = OUT_DIR / f"{trace}_vs_random.csv"
        to_display_random(rnd_prim).to_csv(path, index=False)
        sep = int((rnd_prim["p_holm"] < 0.05).sum())
        print(f"wrote {path.name} ({len(rnd_prim)} paired comparisons, "
              f"{sep} separated from the random control at Holm p<0.05)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
