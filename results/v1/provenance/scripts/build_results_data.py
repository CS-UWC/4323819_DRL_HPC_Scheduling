#!/usr/bin/env python3
"""build_results_data.py

Turn the finished cluster sweep into display-ready CSVs that the manuscript
renders directly via `lib/results.typ`'s `csv-table`.

The pipeline in Project_Github/ owns the *statistics*; this script owns only
*presentation* -- selecting columns, rounding, pretty-printing treatment ids and
marking the best cell per column. It computes no new inferential quantity. The
one exception is Delta%, which is arithmetic on values the pipeline already
emitted.

Best-cell convention: the winning cell in a column is wrapped in `**...**`.
`lib/results.typ` detects that sentinel and renders it orange + bold. Keeping
the direction-of-better logic here means the Typst side needs no metric
knowledge.

Usage:
    python3 scripts/build_results_data.py                  # both traces
    python3 scripts/build_results_data.py --trace physical # one trace only
    python3 scripts/build_results_data.py --check          # verify, write nothing

--trace exists because the two sweeps do not land together. The N27 random
control and the six-way holdout arrived on physical first, and verify() treats
a missing random row as an error, so a whole-run build fails while the
deeplearn sweep is still queued. Building one trace at a time lets the physical
results section proceed; re-run without --trace once deeplearn finishes.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

import pandas as pd

PAPER_DIR = Path(__file__).resolve().parent.parent
CLUSTER = PAPER_DIR.parent / "cluster_results"
OUT_DIR = PAPER_DIR / "data" / "results"
FIG_DIR = PAPER_DIR / "figures" / "results"

TRACES = {"physical": "physical_jobs", "deeplearn": "deeplearn_jobs"}

# Display names match tbl:algorithms in 4323819_Paper.typ (L305-313).
PRETTY = {
    "maskable_ppo": "MaskablePPO",
    "maskable_dqn": "MaskableDQN",
    "maskable_a2c": "MaskableA2C",
    "ppo": "PPO",
    "dqn": "DQN",
    "a2c": "A2C",
    "lcfs": "LCFS",
    "sjf": "SJF",
    "unicep": "UNICEP",
    "random": "Random (masked)",
}

# Presentation order: masked, then unmasked, then the deterministic heuristics,
# then the N27 control last. "Random (masked)" is not a heuristic — it is a
# uniform draw over the valid actions of the same MDP the DRL rows are
# evaluated on, so it is the floor those rows have to clear, and it reads as
# one at the foot of the table. It is the only baseline row with a ± term.
DRL_ORDER = ["maskable_ppo", "maskable_dqn", "maskable_a2c", "ppo", "dqn", "a2c"]

# The unmasked treatments stall and never schedule the complete workload, so
# every number they produce is read off a truncated episode. The manuscript
# (L440) promises a dagger on these rows "within tables and graphs"; attaching
# it to the display name is what keeps that promise in one place, so no table
# can be added later that quietly omits it. make_ci_figures.py marks the same
# set on its forest plots.
UNMASKED = ["ppo", "dqn", "a2c"]
DAGGER = "†"
HEURISTIC_ORDER = ["lcfs", "sjf", "unicep"]
RANDOM_CONTROL = "random"
BASELINE_ORDER = HEURISTIC_ORDER + [RANDOM_CONTROL]

# Each heuristic is run in two backfill configurations, which the pipeline keeps
# apart by treatment_id: "{algo}__mask_false" (backfill on) and
# "{algo}__mask_false__nobf" (off). See Project_Github/src/naming.py.
#
# backfill=OFF is the primary, controlled band and is therefore the one that
# carries the bare name in the tables: HPCsim.step() -- the MDP every DRL row
# and the random control are evaluated on -- has no backfill sweep, so only the
# no-backfill heuristic is the same experiment run with a different policy. The
# backfill=on band is the production reference and is labelled explicitly,
# because a backfilling heuristic beating a non-backfilling agent is a
# statement about backfill as much as about the agent.
#
# Selecting a baseline by `algorithm` alone is ambiguous once both bands exist
# (both rows say "lcfs"), so everything below selects on treatment_id.
NO_BACKFILL_SUFFIX = "__nobf"
BACKFILL_LABEL = {False: "", True: " (backfill)"}


def baseline_treatment_id(algorithm: str, backfill: bool) -> str:
    base = f"{algorithm}__mask_false"
    return base if backfill else base + NO_BACKFILL_SUFFIX


def has_backfill(treatment_id: str) -> bool:
    return not str(treatment_id).endswith(NO_BACKFILL_SUFFIX)


def baseline_label(algorithm: str, backfill: bool) -> str:
    """Display name for one heuristic in one backfill configuration."""
    return pretty(algorithm) + BACKFILL_LABEL[backfill]


def heuristic_rows(baseline: pd.DataFrame) -> list[tuple[str, pd.Series]]:
    """Every heuristic row present, as (display label, row), in table order.

    No-backfill band only. Methodology names backfill=off as the primary,
    controlled band -- it is the same experiment as every DRL row, run with a
    different policy -- so that is what the results tables report. The
    backfill=on rows stay on disk and are discussed in prose; carrying them in
    every table doubled the heuristic block and invited the reader to compare
    across two different environments row by row.
    """
    out = []
    for algo in HEURISTIC_ORDER:
        r = baseline[baseline["treatment_id"]
                     == baseline_treatment_id(algo, False)]
        if not r.empty:
            out.append((baseline_label(algo, False), r.iloc[0]))
    return out

LOWER_IS_BETTER = {
    "avg_waiting", "avg_slowdown", "avg_turnaround", "max_waiting",
    "max_slowdown", "train_h", "eval_wall_s", "decision_latency_mean_ms",
}
HIGHER_IS_BETTER = {"cpu_utilization", "gpu_utilization", "episode_reward"}

# (metric key, column header, format string)
MAIN_METRICS = [
    ("avg_waiting", "Avg Wait (s)", "{:,.0f}"),
    ("avg_slowdown", "Avg Slowdown", "{:,.2f}"),
    ("avg_turnaround", "Avg Turnaround (s)", "{:,.0f}"),
    ("max_waiting", "Max Wait (s)", "{:,.0f}"),
    ("max_slowdown", "Max Slowdown", "{:,.0f}"),
    ("cpu_utilization", "CPU Util", "{:.4f}"),
    ("gpu_utilization", "GPU Util", "{:.4f}"),
]

BEST = "**{}**"

# str.title() on the raw keys yields "Cpu Utilization" and "Decision Latency
# Mean Ms", so the display names are spelled out explicitly.
METRIC_LABEL = {
    "avg_waiting": "Avg waiting",
    "avg_slowdown": "Avg slowdown",
    "avg_turnaround": "Avg turnaround",
    "max_waiting": "Max waiting",
    "max_slowdown": "Max slowdown",
    "cpu_utilization": "CPU utilisation",
    "gpu_utilization": "GPU utilisation",
    "episode_reward": "Episode reward",
    "decision_latency_mean_ms": "Decision latency",
    "eval_wall_s": "Evaluation wall time",
}


def metric_label(key: str) -> str:
    return METRIC_LABEL.get(key, key.replace("_", " ").capitalize())


def pretty(algorithm: str) -> str:
    """Display name, daggered for the treatments that ran truncated episodes.

    Applied at the single point every table label passes through, so the marker
    cannot desynchronise between tables. Anything matching a label back to a
    raw key has to go through `unpretty`.
    """
    name = PRETTY.get(algorithm, algorithm)
    return name + DAGGER if algorithm in UNMASKED else name


def unpretty(label: str) -> str:
    """Raw algorithm key for a display label, dagger or not."""
    stripped = label.removesuffix(DAGGER)
    return next(k for k, v in PRETTY.items() if v == stripped)


def mark_best(values: list[float | None], cells: list[str], metric: str) -> list[str]:
    """Wrap the winning cell for `metric` in the ** sentinel.

    Ties are all marked -- silently picking one winner would misrepresent a tie,
    which matters here because several deeplearn treatments land on identical
    values (e.g. max_slowdown 2290.9 for PPO, SJF and UNICEP).
    """
    if metric not in LOWER_IS_BETTER and metric not in HIGHER_IS_BETTER:
        return cells
    present = [v for v in values if v is not None and pd.notna(v)]
    if not present:
        return cells
    target = min(present) if metric in LOWER_IS_BETTER else max(present)
    return [
        BEST.format(c) if (v is not None and pd.notna(v) and v == target) else c
        for v, c in zip(values, cells)
    ]


def fmt_mean_std(mean: float, std: float | None, spec: str) -> str:
    """Format a cell. Deterministic rows (no seeds) carry no +/- term."""
    if std is None or pd.isna(std):
        return spec.format(mean)
    return f"{spec.format(mean)} ± {spec.format(std)}"


def load_trace(dirname: str) -> dict:
    root = CLUSTER / dirname
    meta = json.loads((root / "aggregate" / "aggregate_metadata.json").read_text())
    return {
        "root": root,
        "algo": pd.read_csv(root / "aggregate" / "algorithm_summary.csv"),
        "seeds": pd.read_csv(root / "aggregate" / "seed_summary.csv"),
        "baseline": pd.read_csv(root / "baseline" / "baseline_summary.csv"),
        "friedman": pd.read_csv(root / "tables" / "friedman_summary.csv"),
        "nemenyi": pd.read_csv(root / "stats" / "pairwise_nemenyi.csv"),
        "ranks": pd.read_csv(root / "stats" / "cd_diagram_input.csv"),
        "vs_baseline": pd.read_csv(root / "baseline" / "baseline_comparison.csv"),
        "train_time": pd.DataFrame(meta["qc_stats"]["train_time_summary"]),
    }


def build_main(d: dict, trace: str) -> pd.DataFrame:
    """Headline table: every treatment and baseline, one row each.

    gpu_utilization is dropped on physical -- it is identically 0.000 for all
    nine rows there (single-resource CPU trace), so a column of zeros would be
    noise and its Friedman row is empty. This is reviewer item G5.
    """
    metrics = [m for m in MAIN_METRICS
               if not (trace == "physical" and m[0] == "gpu_utilization")]

    rows, raw = [], []
    for algo in DRL_ORDER:
        r = d["algo"][d["algo"]["algorithm"] == algo]
        if r.empty:
            continue
        r = r.iloc[0]
        rows.append(pretty(algo))
        raw.append({m: (r[f"{m}_mean_mean"], r[f"{m}_mean_std"]) for m, _, _ in metrics})
    # The std column only exists for a stochastic baseline, and is NaN for the
    # deterministic heuristics, which fmt_mean_std renders without a ± term — so
    # the heuristic rows carry no spread. The random control is the one baseline
    # that must carry its spread: the question it answers ("is MaskablePPO
    # distinguishable from an unlearned masked policy?") cannot be read off a
    # point estimate. .get() rather than [] so a pre-N27 baseline_summary.csv
    # without the column still builds.
    baseline_rows = list(heuristic_rows(d["baseline"]))
    ctrl = d["baseline"][d["baseline"]["algorithm"] == RANDOM_CONTROL]
    if not ctrl.empty:
        baseline_rows.append((pretty(RANDOM_CONTROL), ctrl.iloc[0]))
    for label, r in baseline_rows:
        rows.append(label)
        raw.append({
            m: (r[f"{m}_mean_mean"], r.get(f"{m}_mean_std"))
            for m, _, _ in metrics
        })

    out = {"Algorithm": rows}
    for metric, header, spec in metrics:
        means = [x[metric][0] for x in raw]
        cells = [fmt_mean_std(x[metric][0], x[metric][1], spec) for x in raw]
        out[header] = mark_best(means, cells, metric)
    return pd.DataFrame(out)


def build_ranks(d: dict, metric: str = "avg_waiting") -> pd.DataFrame:
    """RQ2 table: mean rank, and whether the gap to the top rank is significant.

    Mean and median are shown side by side because they disagree sharply for
    deeplearn DQN (rank 2.5, median far below a mean inflated by a few
    diverged seeds). Presenting only one of them makes the rank column look
    like an error.
    """
    ranks = d["ranks"][d["ranks"]["metric_name"] == metric].copy()
    ranks = ranks.sort_values("avg_rank")

    # The reference row is the best *non-truncated* treatment, not simply the
    # best mean rank. On deeplearn the three unmasked treatments take ranks
    # 1-3 on episodes they never finish, so anchoring here would report every
    # "p vs. best" against a policy that never schedules the full workload and
    # would print the best-value highlight on a row the manuscript excludes
    # from all quality claims. Both the anchor and the highlight read this one
    # predicate so they cannot drift apart. Physical is unaffected: its rank
    # leader (MaskablePPO) is already untruncated, which is the check that this
    # is behaving.
    eligible = ranks[~ranks["algorithm"].isin(UNMASKED)]
    ref_row = (eligible if not eligible.empty else ranks).iloc[0]
    top = ref_row["treatment_id"]
    nem = d["nemenyi"][d["nemenyi"]["metric_name"] == metric]

    def p_vs_top(tid: str) -> str:
        if tid == top:
            return "---"
        hit = nem[
            ((nem["treatment_a"] == tid) & (nem["treatment_b"] == top))
            | ((nem["treatment_a"] == top) & (nem["treatment_b"] == tid))
        ]
        if hit.empty:
            return "---"
        p = float(hit.iloc[0]["p_value"])
        sig = bool(hit.iloc[0]["significant"])
        return f"{p:.3f}{'*' if sig else ''}"

    rows = []
    for _, r in ranks.iterrows():
        tid, algo = r["treatment_id"], r["algorithm"]
        vals = d["seeds"][d["seeds"]["treatment_id"] == tid][f"{metric}_mean"]
        rows.append({
            "Algorithm": pretty(algo),
            "Mean Rank": f"{r['avg_rank']:.1f}",
            "Median": f"{vals.median():,.0f}",
            "Mean": f"{vals.mean():,.0f}",
            "p vs. best": p_vs_top(tid),
        })
    df = pd.DataFrame(rows)
    # Highlight the reference row, not row 0: on deeplearn the lowest mean rank
    # belongs to a truncated treatment. Located by display name so it tracks
    # the same predicate the anchor uses.
    ref_label = pretty(ref_row["algorithm"])
    ref_idx = df.index[df["Algorithm"] == ref_label]
    if len(ref_idx):
        df.loc[ref_idx[0], "Mean Rank"] = BEST.format(df.loc[ref_idx[0], "Mean Rank"])
    return df


def build_omnibus(d: dict) -> pd.DataFrame:
    """Friedman + Kendall's W per metric. Rows with no test are dropped."""
    f = d["friedman"].dropna(subset=["p_value"]).copy()
    return pd.DataFrame({
        "Metric": f["metric_name"].map(metric_label),
        # Unicode rather than Typst math: csv-table inserts cells as strings,
        # so "$chi^2$" would render literally.
        "χ²": f["chi2"].map("{:.2f}".format),
        "df": f["df"].astype(int).astype(str),
        "p": f["p_value"].map(lambda p: f"{p:.2e}" if p < 0.001 else f"{p:.3f}"),
        "Kendall's W": f["kendall_w"].map("{:.3f}".format),
        "Interpretation": f["kendall_w_interpretation"],
        "Sig.": f["significant"].map({True: "Yes", False: "No"}),
    })


def build_cost(d: dict) -> pd.DataFrame:
    """RQ3 cost table: training hours, inference cost, decisions, latency.

    The inference-vs-baseline ratio is included deliberately. A reviewer will
    compute it anyway (PPO's deeplearn win costs ~90x the fastest heuristic's
    evaluation time), so it belongs in the table rather than in a rebuttal.
    """
    # Heuristics only. The N27 random control is in baseline_summary.csv but is
    # not a heuristic: its wall time is an MDP rollout over the same env the DRL
    # rows use, so folding it into a "fastest heuristic" denominator would
    # silently change what this column means.
    #
    # No-backfill band only, as everywhere else: a ratio whose numerator and
    # denominator come from different backfill configurations is not a ratio of
    # anything, and backfill=off is the configuration the DRL rows are run in.
    heuristics = d["baseline"][
        d["baseline"]["treatment_id"].isin(
            [baseline_treatment_id(a, False) for a in HEURISTIC_ORDER])
    ]
    fastest_baseline = heuristics["eval_wall_s_mean_mean"].min()
    ratio_header = "Eval Ratio"

    rows, train_h, evals, lats = [], [], [], []
    for algo in DRL_ORDER:
        a = d["algo"][d["algo"]["algorithm"] == algo]
        t = d["train_time"][d["train_time"]["algorithm"] == algo]
        if a.empty or t.empty:
            continue
        a, t = a.iloc[0], t.iloc[0]
        rows.append(pretty(algo))
        train_h.append((t["mean"] / 3600.0, t["std"] / 3600.0, int(t["count"])))
        evals.append(a["eval_wall_s_mean_mean"])
        lats.append(a["decision_latency_mean_ms_mean_mean"])

    df = pd.DataFrame({
        "Algorithm": rows,
        "Train (h)": mark_best(
            [h for h, _, _ in train_h],
            [f"{h:.2f} ± {s:.2f}" for h, s, _ in train_h],
            "train_h"),
        "Runs": [str(n) for _, _, n in train_h],
        "Eval (s)": mark_best(evals, [f"{v:,.0f}" for v in evals], "eval_wall_s"),
        ratio_header: [f"{v / fastest_baseline:,.0f}×" for v in evals],
        "Latency (ms)": mark_best(
            lats, [f"{v:.2f}" for v in lats], "decision_latency_mean_ms"),
    })
    return df


def build_vs_baseline(d: dict) -> pd.DataFrame:
    """Best-DRL vs each heuristic, as produced by the pipeline.

    Delta% is added beside every p-value: at n=10 the smallest attainable
    two-sided Wilcoxon p is (1/2)^9 = 0.001953, and most rows sit exactly on
    that floor. The p-value therefore reports consistency across seeds, not
    magnitude, and is misleading without the effect size next to it.
    """
    v = d["vs_baseline"].copy()
    # No-backfill band only, matching heuristic_rows(): a DRL row is compared
    # against the heuristic run in the same environment it was evaluated in.
    # The pipeline emits both bands, so this filters rather than assumes.
    v = v[~v["baseline_treatment_id"].map(has_backfill)].reset_index(drop=True)
    delta = (v["drl_mean"] - v["baseline_value"]) / v["baseline_value"] * 100.0
    heuristic = [str(t).split("__")[0].upper() for t in v["baseline_treatment_id"]]
    return pd.DataFrame({
        "Metric": v["metric"].map(metric_label),
        "Heuristic": heuristic,
        "Heuristic value": v["baseline_value"].map("{:,.3f}".format),
        "DRL mean": v["drl_mean"].map("{:,.3f}".format),
        "Δ%": delta.map(lambda x: f"{x:+.1f}%"),
        "p": v["p_value"].map(lambda p: "---" if pd.isna(p) else f"{p:.4f}"),
        "DRL better": v["drl_better"].map({True: "Yes", False: "No"}).fillna("---"),
    })


def winner_treatment(dirname: str) -> str:
    """The Pareto-selected treatment_id for a trace, from select_best's output."""
    path = CLUSTER / dirname / "best" / "best_algorithm.json"
    return json.loads(path.read_text())["treatment_id"]


def build_holdout(traces: dict[str, str]) -> pd.DataFrame:
    """One row per trace: the Pareto winner's held-out performance.

    Selects the winner by treatment_id rather than taking the first row.
    Before M5b, holdout_summary.csv held exactly one treatment and .iloc[0] was
    unambiguous; it now holds all six, and .iloc[0] would silently print
    whichever happened to sort first — a wrong number in the paper with nothing
    to flag it. The six-way view lives in build_holdout_all().

    Under --trace this table is rebuilt for the selected trace only and merged
    over the previous file, so building physical alone does not silently delete
    the deeplearn row from a table the manuscript already renders.
    """
    rows = []
    for trace, dirname in traces.items():
        summary = pd.read_csv(CLUSTER / dirname / "holdout" / "holdout_summary.csv")
        win = winner_treatment(dirname)
        match = summary[summary["treatment_id"] == win]
        if match.empty:
            raise SystemExit(
                f"{trace}: Pareto winner {win!r} has no row in holdout_summary.csv "
                f"(present: {sorted(summary['treatment_id'])})")
        h = match.iloc[0]
        rows.append({
            "Trace": trace.capitalize(),
            "Algorithm": pretty(h["algorithm"]),
            "Avg Wait (s)": f"{h['avg_waiting_mean_mean']:,.0f} ± {h['avg_waiting_mean_std']:,.0f}",
            "Avg Slowdown": f"{h['avg_slowdown_mean_mean']:,.2f} ± {h['avg_slowdown_mean_std']:,.2f}",
            "Avg Turnaround (s)": f"{h['avg_turnaround_mean_mean']:,.0f}",
            "Max Slowdown": f"{h['max_slowdown_mean_mean']:,.0f}",
            "CPU Util": f"{h['cpu_utilization_mean_mean']:.4f}",
        })
    df = pd.DataFrame(rows)

    # Carry forward rows for traces this invocation did not rebuild.
    prev_path = OUT_DIR / "holdout.csv"
    if len(traces) < len(TRACES) and prev_path.exists():
        prev = pd.read_csv(prev_path)
        keep = prev[~prev["Trace"].isin(df["Trace"])]
        df = pd.concat([df, keep], ignore_index=True)
        order = [t.capitalize() for t in TRACES]
        df = df.sort_values(
            "Trace", key=lambda s: s.map(order.index)).reset_index(drop=True)
    return df


def build_holdout_all(d: dict, dirname: str, metric: str = "avg_waiting") -> pd.DataFrame:
    """All six treatments, dev vs held-out, with the rank in each (M5b).

    This is the table that retires M5. The dev-vs-holdout *values* are not
    comparable — the two splits are different workloads (physical: 58,894 dev
    jobs vs 25,241 holdout), and on deeplearn they move in opposite directions,
    so a raw value comparison reads as out-of-sample collapse when it is really
    a change of workload (M5a). What transfers is the **ordering**: if the
    six-way ranking survives out of sample, the in-sample advantage did not
    manufacture it, and M5 stops being a threat-to-validity paragraph.

    Both columns are therefore ranked independently within their own split, and
    the rank columns — not the values — are what the argument rests on.
    """
    holdout = pd.read_csv(CLUSTER / dirname / "holdout" / "holdout_summary.csv")
    dev = d["algo"]
    col = f"{metric}_mean_mean"
    std = f"{metric}_mean_std"

    rows = []
    for algo in DRL_ORDER:
        dv = dev[dev["algorithm"] == algo]
        hv = holdout[holdout["algorithm"] == algo]
        if dv.empty or hv.empty:
            continue
        dv, hv = dv.iloc[0], hv.iloc[0]
        rows.append({
            "Algorithm": pretty(algo),
            "_dev": dv[col], "_hold": hv[col],
            "Dev": f"{dv[col]:,.0f} ± {dv[std]:,.0f}",
            "Holdout": f"{hv[col]:,.0f} ± {hv[std]:,.0f}",
        })
    if not rows:
        return pd.DataFrame()

    out = pd.DataFrame(rows)
    ascending = metric in LOWER_IS_BETTER
    out["Dev rank"] = out["_dev"].rank(ascending=ascending, method="min").astype(int)
    out["Holdout rank"] = out["_hold"].rank(ascending=ascending, method="min").astype(int)
    out["Δ rank"] = (out["Holdout rank"] - out["Dev rank"]).map(lambda x: f"{x:+d}")
    return out[["Algorithm", "Dev", "Dev rank", "Holdout", "Holdout rank", "Δ rank"]]


def build_holdout_margin(d: dict, dirname: str,
                         metric: str = "avg_waiting") -> pd.DataFrame:
    """M5a: the selected treatment's margin against each reference, dev vs holdout.

    The raw dev-vs-holdout *value* comparison is meaningless here -- the two
    splits are different workloads, so every treatment's absolute waiting time
    falls out of sample and a reader who compares the columns concludes the
    agent improved. What can legitimately be compared across splits is the
    *margin* against a reference evaluated on the same split: if the agent is
    +6% against LCFS in sample and +6% out of sample, the in-sample advantage
    did not inflate the comparison, which is what M5 needs.

    References are the no-backfill band plus the random control -- the
    like-for-like set, since the agent has no backfill action. The shift column
    is the honest answer and it is not always small: on physical the margins
    move by 3-9 pp and in both directions, so the surviving claim is about
    ordering, not magnitude. Reporting the shift is the point of the table.

    Empty (and skipped by main) when the trace has no baseline_holdout sweep.
    """
    hold_base_path = CLUSTER / dirname / "baseline_holdout" / "baseline_summary.csv"
    if not hold_base_path.exists():
        return pd.DataFrame()

    col = f"{metric}_mean_mean"
    std = f"{metric}_mean_std"
    dev_base = d["baseline"]
    hold_base = pd.read_csv(hold_base_path)
    hold_drl = pd.read_csv(CLUSTER / dirname / "holdout" / "holdout_summary.csv")

    win = winner_treatment(dirname)
    hw = hold_drl[hold_drl["treatment_id"] == win]
    if hw.empty:
        raise SystemExit(
            f"{dirname}: selected treatment {win!r} has no holdout row")
    algorithm = hw.iloc[0]["algorithm"]
    dw = d["algo"][d["algo"]["algorithm"] == algorithm]
    if dw.empty:
        raise SystemExit(
            f"{dirname}: selected treatment {win!r} has no dev row")
    dev_val, hold_val = dw.iloc[0][col], hw.iloc[0][col]

    # Heuristics are selected on treatment_id because the two backfill bands
    # share an `algorithm`; the random control carries mask_true and so does not
    # match baseline_treatment_id(), and is selected on `algorithm` instead.
    def ref_value(frame: pd.DataFrame, key: str, by_algorithm: bool) -> float | None:
        r = frame[frame["algorithm" if by_algorithm else "treatment_id"] == key]
        return None if r.empty else float(r.iloc[0][col])

    # The selected treatment's own values first, so the table reads standalone.
    rows = [{
        "Reference": f"{pretty(algorithm)} (selected)",
        "Dev": fmt_mean_std(dev_val, dw.iloc[0][std], "{:,.0f}"),
        "Dev Δ%": "---",
        "Holdout": fmt_mean_std(hold_val, hw.iloc[0][std], "{:,.0f}"),
        "Holdout Δ%": "---",
        "Shift (pp)": "---",
    }]

    references = [(baseline_treatment_id(a, False), baseline_label(a, False), False)
                  for a in HEURISTIC_ORDER]
    references.append((RANDOM_CONTROL, pretty(RANDOM_CONTROL), True))
    for key, label, by_algorithm in references:
        dv = ref_value(dev_base, key, by_algorithm)
        hv = ref_value(hold_base, key, by_algorithm)
        if dv is None or hv is None:
            continue
        dm = (dev_val - dv) / dv * 100.0
        hm = (hold_val - hv) / hv * 100.0
        rows.append({
            "Reference": label,
            "Dev": f"{dv:,.0f}",
            "Dev Δ%": f"{dm:+.1f}%",
            "Holdout": f"{hv:,.0f}",
            "Holdout Δ%": f"{hm:+.1f}%",
            "Shift (pp)": f"{hm - dm:+.1f}",
        })
    return pd.DataFrame(rows)


# BF-02: the backfill control band table. Every other results table reports the
# no-backfill band only (see heuristic_rows) -- this is the one place both bands
# are shown side by side, so the reader can see what the control actually cost
# the heuristics instead of taking the prose's word for it.
#
# Orientation is fixed by the section it serves: for each heuristic the first
# column is backfill DISABLED and the second ENABLED. Disabled comes first
# because it is the band every later table quotes; enabled is the production
# reference being deviated from, so it reads as the annotation, not the datum.
#
# The three average metrics only. The maxima and the two utilisation metrics
# were dropped after seeing them rendered: max_waiting and max_slowdown are
# single-job order-of-arrival artefacts rather than properties of the band, and
# cpu/gpu_utilization are trace-fixed under full-trace replay (RL-07) -- on
# deeplearn all six utilisation cells were identical to four decimals, and on
# physical GPU was identically zero. Seven metrics bought two columns of
# constants at the cost of a table too wide to read. The operational metrics are
# excluded for a different reason: eval_wall_s is a property of the simulator's
# reservation-and-rollback loop rather than of the schedule, so putting it in
# this grid would invite reading a 4-18x wall-clock ratio as a scheduling
# result. BF-04 handles that in prose.
#
# Headers are spelled exactly as MAIN_METRICS spells them, so the same quantity
# never appears under two names across tbl:phys-main, tbl:dl-main and this one.
BAND_METRICS = [
    (k, h, f) for (k, h, f) in MAIN_METRICS
    if k in ("avg_waiting", "avg_slowdown", "avg_turnaround")
]

# Backfill enabled first, matching tbl:environ_config's True/False spelling.
BAND_ORDER = [True, False]


def _band_value(base: pd.DataFrame, algo: str, backfill: bool,
                metric: str) -> float | None:
    r = base[base["treatment_id"] == baseline_treatment_id(algo, backfill)]
    if r.empty:
        return None
    v = r.iloc[0][f"{metric}_mean_mean"]
    return None if pd.isna(v) else float(v)


def build_backfill_bands(traces: dict[str, str]) -> pd.DataFrame:
    """Both backfill bands for all three heuristics, both traces, one table.

    One row per (trace, heuristic, band); one column per metric. The two rows of
    a heuristic are adjacent, so the comparison the section is about reads down
    a two-row pair. Trace and Algorithm are printed once per group and left
    blank on the continuation row, and the manuscript draws an extra midrule
    after the physical block so the two traces read as separate panels of one
    table rather than as twelve unrelated rows.

    The better band of each pair is marked with the ** sentinel. That is a
    departure from this file's usual best-cell convention, which marks the
    winner of a whole *column*: here the comparison of interest runs within the
    pair, and comparing LCFS against SJF is not what this table is for. The
    caption says so. Ties are marked on neither row -- equality means backfill
    changed nothing, which is a finding in its own right, and orange on both
    rows would read as two winners rather than as no difference.
    """
    frames = []
    for trace, dirname in traces.items():
        base = pd.read_csv(CLUSTER / dirname / "baseline" / "baseline_summary.csv")
        missing = [
            baseline_treatment_id(a, b)
            for a in HEURISTIC_ORDER for b in BAND_ORDER
            if base[base["treatment_id"] == baseline_treatment_id(a, b)].empty
        ]
        if missing:
            raise SystemExit(
                f"{trace}: backfill band table needs both bands for every "
                f"heuristic; missing {missing}")

        rows = []
        for algo in HEURISTIC_ORDER:
            # Both rows of the pair are formatted before either is emitted, so
            # the winner can be decided on the rendered strings.
            cells: dict[bool, dict[str, str]] = {b: {} for b in BAND_ORDER}
            for metric, label, spec in BAND_METRICS:
                vals = {b: _band_value(base, algo, b, metric) for b in BAND_ORDER}
                for b in BAND_ORDER:
                    v = vals[b]
                    cells[b][label] = "—" if v is None else spec.format(v)
                # Compare the *rendered* strings, not the raw floats: a
                # difference below display precision would print a highlighted
                # cell beside an identical-looking plain one and assert a winner
                # the reader cannot see.
                on, off = vals[True], vals[False]
                if (on is not None and off is not None
                        and cells[True][label] != cells[False][label]
                        and metric in (LOWER_IS_BETTER | HIGHER_IS_BETTER)):
                    on_wins = (on < off if metric in LOWER_IS_BETTER
                               else on > off)
                    cells[on_wins][label] = BEST.format(cells[on_wins][label])

            for b in BAND_ORDER:
                rows.append({
                    "Trace": trace.capitalize(),
                    "Algorithm": pretty(algo),
                    "Backfill": str(b),
                    **cells[b],
                })
        frames.append(pd.DataFrame(rows))

    df = pd.concat(frames, ignore_index=True)

    # Carry forward the panel for a trace this invocation did not rebuild, so
    # --trace physical does not silently delete the deeplearn half of a table
    # the manuscript already renders. Same contract as build_holdout.
    prev_path = OUT_DIR / "backfill_bands.csv"
    if len(traces) < len(TRACES) and prev_path.exists():
        prev = pd.read_csv(prev_path).fillna("")
        # The stored file blanks repeated labels for display; refill them so the
        # carry-forward can select on Trace.
        prev["Trace"] = prev["Trace"].replace("", None).ffill()
        prev["Algorithm"] = prev["Algorithm"].replace("", None).ffill()
        keep = prev[~prev["Trace"].isin(df["Trace"])]
        df = pd.concat([df, keep], ignore_index=True)
    order = [t.capitalize() for t in TRACES]
    df = df.sort_values("Trace", key=lambda s: s.map(order.index),
                        kind="stable").reset_index(drop=True)

    # Print each label once per group. Repeating "Physical" six times and each
    # heuristic twice is noise the midrule and the row pairing already convey.
    # Algorithm is blanked within its trace, not globally -- LCFS appears in
    # both panels and the second one must still be labelled.
    df["Algorithm"] = df.groupby("Trace", sort=False)["Algorithm"].transform(
        lambda s: s.mask(s.duplicated(), ""))
    df["Trace"] = df["Trace"].mask(df["Trace"].duplicated(), "")
    return df


FIGURES = [
    ("physical_jobs", "cd_diagram_avg_waiting"),
    ("physical_jobs", "cd_diagram_max_slowdown"),
    ("physical_jobs", "page_trend_avg_waiting"),
    ("deeplearn_jobs", "cd_diagram_avg_waiting"),
    ("deeplearn_jobs", "page_trend_avg_waiting"),
]


def stage_figures(traces: dict[str, str], check: bool) -> list[str]:
    """Copy pipeline plots into the paper tree.

    Typst resolves paths against the entry file's directory, so anything the
    manuscript reads has to live under Submmisions/. Both .pdf and .png are
    staged so the figures can be swapped without touching the .typ.

    bar_graph_* is deliberately NOT staged -- see make_result_figures.py.
    """
    problems = []
    for dirname, stem in FIGURES:
        trace = "physical" if dirname.startswith("physical") else "deeplearn"
        if trace not in traces:
            continue
        for ext in ("pdf", "png"):
            src = CLUSTER / dirname / "plots" / f"{stem}.{ext}"
            dst = FIG_DIR / f"{trace}_{stem}.{ext}"
            if not src.exists():
                problems.append(f"missing source figure: {src}")
                continue
            if check:
                if not dst.exists():
                    problems.append(f"figure not staged: {dst.name}")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
    return problems


def verify(tables: dict[str, pd.DataFrame],
           traces: dict[str, str]) -> list[str]:
    """Re-derive independently of the builders and assert agreement.

    Deliberately reads the source CSVs again rather than trusting the frames
    that were just built, so a bug in a builder cannot validate itself.
    """
    problems = []

    for trace, dirname in traces.items():
        algo = pd.read_csv(CLUSTER / dirname / "aggregate" / "algorithm_summary.csv")
        base = pd.read_csv(CLUSTER / dirname / "baseline" / "baseline_summary.csv")
        main = tables[f"{trace}_main"]

        # The with-backfill heuristic rows exist on disk but are deliberately
        # not reported (see heuristic_rows), so they are excluded here too --
        # otherwise this check would demand the rows the tables just dropped.
        # has_backfill() is only meaningful for heuristics: the random control's
        # id is random__mask_true, which carries no band suffix.
        reported_base = base[~(base["treatment_id"].map(has_backfill)
                               & base["algorithm"].isin(HEURISTIC_ORDER))]
        expected_rows = len(algo) + len(reported_base)
        if len(main) != expected_rows:
            problems.append(
                f"{trace}_main: {len(main)} rows, expected {expected_rows} "
                f"({len(algo)} DRL + {len(reported_base)} reported baselines)")

        # Exactly one winner per metric column, unless the values genuinely tie.
        for col in main.columns:
            if col == "Algorithm":
                continue
            n = main[col].str.startswith("**").sum()
            if n == 0:
                problems.append(f"{trace}_main: no best cell marked in '{col}'")

        if trace == "physical" and "GPU Util" in main.columns:
            problems.append("physical_main: GPU Util must be dropped (G5)")

        # Two rows with the same label would be the band-labelling silently
        # failing — the reader would see two "LCFS" rows carrying different
        # numbers, which is worse than not running the second configuration.
        dupes = main["Algorithm"][main["Algorithm"].duplicated()].tolist()
        if dupes:
            problems.append(
                f"{trace}_main: duplicate row labels {sorted(set(dupes))} — the "
                f"backfill band is not being distinguished")

        # Report which heuristic bands are present, so a half-run sweep is
        # visible in the build output rather than only in the rendered table.
        bands = sorted({
            ("backfill" if has_backfill(t) else "no backfill")
            for t in base["treatment_id"]
            if str(t).split("__")[0] in HEURISTIC_ORDER
        })
        print(f"[{trace}] heuristic bands present: {', '.join(bands) or 'none'}")

        # N27 control: it is only a control if its spread is reported. A point
        # estimate cannot answer "is MaskablePPO distinguishable from an
        # unlearned masked policy?", and a lost std would be invisible in the
        # rendered table, so assert it here rather than trusting the pipeline.
        ctrl = base[base["algorithm"] == RANDOM_CONTROL]
        if ctrl.empty:
            problems.append(
                f"{trace}: no '{RANDOM_CONTROL}' row in baseline_summary.csv — "
                f"the N27 random-policy control has not been run for this trace")
        else:
            n_seeds = int(ctrl.iloc[0].get("n_seeds", 0))
            if n_seeds < 2:
                problems.append(
                    f"{trace}: random control has n_seeds={n_seeds}; it is "
                    f"stochastic and needs the full seed set to carry a std")
            cell = main.loc[main["Algorithm"] == pretty(RANDOM_CONTROL),
                            "Avg Wait (s)"].iloc[0]
            if "±" not in cell:
                problems.append(
                    f"{trace}_main: random control cell '{cell}' has no ± term")

        # Spot-check one headline value end to end.
        for algorithm, metric, header, spec in [
            ("maskable_ppo", "avg_waiting", "Avg Wait (s)", "{:,.0f}"),
            ("ppo", "avg_waiting", "Avg Wait (s)", "{:,.0f}"),
        ]:
            r = algo[algo["algorithm"] == algorithm]
            if r.empty:
                continue
            r = r.iloc[0]
            want = fmt_mean_std(r[f"{metric}_mean_mean"], r[f"{metric}_mean_std"], spec)
            got = main.loc[main["Algorithm"] == pretty(algorithm), header].iloc[0]
            if got.strip("*") != want:
                problems.append(
                    f"{trace}_main {pretty(algorithm)}/{header}: got '{got}' want '{want}'")

        # Training hours must round-trip from the raw seconds in the metadata.
        meta = json.loads(
            (CLUSTER / dirname / "aggregate" / "aggregate_metadata.json").read_text())
        tt = {t["algorithm"]: t for t in meta["qc_stats"]["train_time_summary"]}
        cost = tables[f"{trace}_cost"]
        for _, row in cost.iterrows():
            algorithm = unpretty(row["Algorithm"])
            want = f"{tt[algorithm]['mean'] / 3600.0:.2f}"
            if want not in row["Train (h)"]:
                problems.append(
                    f"{trace}_cost {row['Algorithm']}: train hours "
                    f"'{row['Train (h)']}' does not contain '{want}'")

    # ── backfill band table (BF-02) ──────────────────────────────────────────
    # The failure this guards against is the two bands being swapped. Nothing in
    # the rendered table would look wrong if they were -- both rows carry
    # plausible numbers -- but every later table quotes the no-backfill band, so
    # a swap would put the paper's own baselines in the row labelled as the
    # configuration it says it did not use. Re-derive from source, then
    # cross-check the Backfill=False rows against what *_main published.
    bands = tables.get("backfill_bands")
    if bands is not None:
        panel = bands.copy().fillna("")
        panel["Trace"] = panel["Trace"].replace("", None).ffill()
        panel["Algorithm"] = panel["Algorithm"].replace("", None).ffill()
        want_rows = len(HEURISTIC_ORDER) * len(BAND_ORDER)
        for trace, dirname in traces.items():
            got = panel[panel["Trace"] == trace.capitalize()]
            if len(got) != want_rows:
                problems.append(
                    f"backfill_bands: {trace} panel has {len(got)} rows, "
                    f"expected {want_rows}")
                continue
            base = pd.read_csv(CLUSTER / dirname / "baseline" / "baseline_summary.csv")
            main = tables[f"{trace}_main"]
            for algo in HEURISTIC_ORDER:
                for backfill in BAND_ORDER:
                    r = got[(got["Algorithm"] == pretty(algo))
                            & (got["Backfill"] == str(backfill))]
                    if len(r) != 1:
                        problems.append(
                            f"backfill_bands {trace}/{pretty(algo)}: "
                            f"{len(r)} rows with Backfill={backfill}, expected 1")
                        continue
                    src = base[base["treatment_id"]
                               == baseline_treatment_id(algo, backfill)].iloc[0]
                    for metric, label, spec in BAND_METRICS:
                        want = spec.format(src[f"{metric}_mean_mean"])
                        cell = str(r.iloc[0][label]).strip("*")
                        if cell != want:
                            problems.append(
                                f"backfill_bands {trace}/{pretty(algo)}/"
                                f"Backfill={backfill}/{label}: "
                                f"got '{cell}' want '{want}'")

                # Backfill=False is the band *_main reports, so the two tables
                # must agree cell for cell on every shared metric. This is the
                # check that catches a swap: it compares against a number
                # derived by a completely separate builder.
                off = got[(got["Algorithm"] == pretty(algo))
                          & (got["Backfill"] == "False")]
                mrow = main[main["Algorithm"] == pretty(algo)]
                if off.empty or mrow.empty:
                    continue
                for metric, label, _ in BAND_METRICS:
                    header = next((h for k, h, _ in MAIN_METRICS if k == metric), None)
                    if header is None or header not in main.columns:
                        continue
                    a = str(off.iloc[0][label]).strip("*")
                    b = str(mrow.iloc[0][header]).strip("*")
                    if a != b:
                        problems.append(
                            f"backfill_bands vs {trace}_main, {pretty(algo)} "
                            f"{label}: '{a}' vs '{b}' — the bands may be swapped")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify against source and write nothing")
    ap.add_argument("--trace", action="append", choices=sorted(TRACES),
                    help="build only this trace (repeatable). Default: both. "
                         "Use while the other sweep is still running.")
    args = ap.parse_args()

    if not CLUSTER.exists():
        print(f"error: cluster results not found at {CLUSTER}", file=sys.stderr)
        return 2

    traces = ({t: TRACES[t] for t in args.trace} if args.trace else dict(TRACES))

    tables: dict[str, pd.DataFrame] = {}
    for trace, dirname in traces.items():
        d = load_trace(dirname)
        tables[f"{trace}_main"] = build_main(d, trace)
        tables[f"{trace}_ranks"] = build_ranks(d)
        tables[f"{trace}_omnibus"] = build_omnibus(d)
        tables[f"{trace}_cost"] = build_cost(d)
        tables[f"{trace}_vs_baseline"] = build_vs_baseline(d)
        # M5b: empty until the six-way holdout has been run, so skip rather than
        # writing a header-only CSV that Typst would render as a blank table.
        holdout_all = build_holdout_all(d, dirname)
        if not holdout_all.empty:
            tables[f"{trace}_holdout_all"] = holdout_all
        # M5a: needs the baseline_holdout sweep, which lands separately from the
        # DRL holdout, so skip rather than fail while it is still queued.
        margin = build_holdout_margin(d, dirname)
        if not margin.empty:
            tables[f"{trace}_holdout_margin"] = margin
    tables["holdout"] = build_holdout(traces)
    tables["backfill_bands"] = build_backfill_bands(traces)

    problems = verify(tables, traces)
    problems += stage_figures(traces, check=args.check)

    if args.check:
        if problems:
            print("FAIL")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"OK — {len(tables)} tables verified against source")
        return 0

    if problems:
        print("FAIL (not written)")
        for p in problems:
            print(f"  - {p}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(OUT_DIR / f"{name}.csv", index=False)
        print(f"wrote data/results/{name}.csv  ({len(df)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
