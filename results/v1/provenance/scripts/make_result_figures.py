#!/usr/bin/env python3
"""make_result_figures.py

Draw the DRL-vs-heuristic bar comparison the pipeline's version fails to draw.

Why this exists rather than reusing Project_Github/src/visualise.py:
`draw_bar_graphs` (visualise.py:362) is handed only `seed_summary.csv`, which
contains DRL treatments. The heuristics live in a separate `baseline_summary.csv`
that is never merged in, so its baseline-colour comprehension never matches, all
bars render steelblue, and the legend still advertises a "Baseline" series with
nothing behind it. The upstream fix is tracked in paper_review.md; the manuscript
does not wait on a pipeline re-run.

This is a DESCRIPTIVE figure. The heuristics are deterministic single runs, so
putting them on the same axis is a visual comparison, not a hypothesis test --
the tests live in `<trace>_equivalence.csv` (baseline_equivalence.py).

Two deliberate choices:

* Error bars are bootstrap 95% CIs of the mean, not +/- 1 SD. An SD describes
  the spread of seeds; a CI describes how well the mean is pinned down, which
  is what "does this overlap the heuristic" actually asks. A2C and DQN have
  SDs larger than their means, so SD bars would render as noise.
* Heuristics are drawn both as bars and as horizontal rules across the panel,
  so whether a DRL interval crosses a heuristic is readable directly.

Usage:
    python3 scripts/make_result_figures.py
    python3 scripts/make_result_figures.py --trace physical
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

PAPER_DIR = Path(__file__).resolve().parent.parent
CLUSTER = PAPER_DIR.parent / "cluster_results"
FIG_DIR = PAPER_DIR / "figures" / "results"

TRACES = {"physical": "physical_jobs", "deeplearn": "deeplearn_jobs"}

PRETTY = {
    "maskable_ppo": "MaskablePPO", "maskable_dqn": "MaskableDQN",
    "maskable_a2c": "MaskableA2C", "ppo": "PPO", "dqn": "DQN", "a2c": "A2C",
    "lcfs": "LCFS", "sjf": "SJF", "unicep": "UNICEP",
    "random": "Random",
}
DRL_ORDER = ["maskable_ppo", "maskable_dqn", "maskable_a2c", "ppo", "dqn", "a2c"]
BASELINE_ORDER = ["lcfs", "sjf", "unicep"]

# The unmasked treatments never schedule the complete workload, so their bars
# are read off truncated episodes. Marked with the same dagger the tables and
# the CI forests in make_ci_figures.py use, in mathtext because these labels go
# through matplotlib rather than typst.
UNMASKED = {"ppo", "dqn", "a2c"}


def pretty(algo: str) -> str:
    return PRETTY[algo] + ("$^\\dagger$" if algo in UNMASKED else "")

# The N27 control, drawn last and in its own colour. It is not a heuristic --
# it is a uniform draw over the valid actions of the same MDP the DRL bars are
# evaluated on, i.e. the floor those bars have to clear. It is stochastic over
# the same ten seeds, so unlike the heuristics it carries a real CI, and it is
# the one reference line whose position the DRL bars are supposed to beat.
RANDOM_CONTROL = "random"

# Each heuristic is run in two backfill configurations, kept apart by
# treatment_id ("{algo}__mask_false" on, "{algo}__mask_false__nobf" off). Only
# backfill=off is drawn: it is the controlled band (HPCsim.step(), the MDP the
# DRL bars run on, has no backfill sweep), which is what Methodology names as
# the primary comparison. Drawing both put two reference lines per heuristic on
# a figure whose point is where the DRL bars land relative to one band.
# Selecting on `algorithm` alone would take .iloc[0] of two rows and silently
# draw whichever came first. See Project_Github/src/naming.py.
NO_BACKFILL_SUFFIX = "__nobf"


def baseline_bands(base: pd.DataFrame) -> list[tuple[str, pd.Series]]:
    """(label, row) for each no-backfill heuristic present, in draw order."""
    out = []
    for algo in BASELINE_ORDER:
        tid = f"{algo}__mask_false{NO_BACKFILL_SUFFIX}"
        r = base.loc[base["treatment_id"] == tid]
        if not r.empty:
            out.append((PRETTY[algo], r.iloc[0]))
    return out

# Metrics whose across-treatment spread covers orders of magnitude. The diverged
# treatments sit ~1000x above the converged ones, so a linear axis renders every
# useful bar as a flat line.
LOG_METRICS = {"avg_waiting", "avg_turnaround", "max_waiting",
               "max_slowdown", "avg_slowdown"}

METRICS = [
    ("avg_waiting", "Average waiting time (s)"),
    ("avg_slowdown", "Average slowdown"),
    ("max_slowdown", "Maximum slowdown"),
    ("cpu_utilization", "CPU utilisation"),
]

DRL_COLOR = "#4C72B0"
BASE_COLOR = "#DD8452"
RAND_COLOR = "#8C8C8C"
ACCENT = "#D2691E"

# Roughly the manuscript's body font, so figure text does not read larger than
# the surrounding prose once placed in a two-column 9pt layout.
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Linux Libertine O", "Linux Libertine", "DejaVu Serif"],
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
})


def bootstrap_ci(values: np.ndarray, n_boot: int = 10_000,
                 alpha: float = 0.05, seed: int = 0) -> tuple[float, float]:
    """Percentile bootstrap CI of the mean.

    Seeded so the figure is byte-reproducible across runs -- a resampled CI
    that shifts slightly on every rebuild would be an odd thing to ship in a
    reproducibility-focused paper.
    """
    rng = np.random.default_rng(seed)
    if len(values) < 2:
        return float(values[0]), float(values[0])
    means = rng.choice(values, size=(n_boot, len(values)), replace=True).mean(axis=1)
    return (float(np.percentile(means, 100 * alpha / 2)),
            float(np.percentile(means, 100 * (1 - alpha / 2))))


FOCUS_FACTOR = 2.0


def collect(seeds: pd.DataFrame, base: pd.DataFrame, rnd: pd.DataFrame,
            metric: str) -> dict:
    names, means, los, his, kinds = [], [], [], [], []

    for algo in DRL_ORDER:
        vals = seeds.loc[seeds["algorithm"] == algo, f"{metric}_mean"]
        if vals.empty:
            continue
        v = vals.to_numpy(dtype=float)
        lo, hi = bootstrap_ci(v)
        names.append(pretty(algo))
        means.append(float(v.mean()))
        los.append(lo)
        his.append(hi)
        kinds.append("drl")

    for label, row in baseline_bands(base):
        m = float(row[f"{metric}_mean_mean"])
        names.append(label)
        means.append(m)
        los.append(m)              # deterministic: a single run, no interval
        his.append(m)
        kinds.append("heuristic")

    # Drawn from the per-seed rows, not the summary mean, so the control gets a
    # bootstrap CI on the same footing as the DRL bars.
    if not rnd.empty and metric in rnd.columns:
        v = rnd[metric].to_numpy(dtype=float)
        lo, hi = bootstrap_ci(v)
        names.append(PRETTY[RANDOM_CONTROL])
        means.append(float(v.mean()))
        los.append(lo)
        his.append(hi)
        kinds.append("random")

    kinds = np.asarray(kinds)
    return {
        "names": np.asarray(names), "means": np.asarray(means),
        "los": np.asarray(los), "his": np.asarray(his),
        "kinds": kinds,
        "is_base": kinds != "drl",
    }


def focus_mask(d: dict, metric: str) -> np.ndarray:
    """Keep only treatments competitive with the best, plus every heuristic.

    The full-field view has to be log-scaled because the diverged treatments sit
    ~1000x above the rest, which flattens the comparison that actually matters:
    PPO at 818 s against LCFS at 860 s is invisible on a three-decade axis. This
    mask drives a companion linear-axis panel where a few percent is legible.
    """
    means = d["means"]
    if metric.endswith("utilization"):
        keep = means >= means.max() / FOCUS_FACTOR
    else:
        keep = means <= means.min() * FOCUS_FACTOR
    return keep | d["is_base"]


def draw(trace: str, dirname: str) -> list[Path]:
    root = CLUSTER / dirname
    seeds = pd.read_csv(root / "aggregate" / "seed_summary.csv")
    base = pd.read_csv(root / "baseline" / "baseline_summary.csv")
    wide = pd.read_csv(root / "baseline" / "baseline_eval_wide.csv")
    rnd = wide[wide["algorithm"] == RANDOM_CONTROL].dropna(subset=["seed"])

    written = []
    for metric, label in METRICS:
        full = collect(seeds, base, rnd, metric)
        views = [("bar", full, True)]

        keep = focus_mask(full, metric)
        if 1 < keep.sum() < len(keep):
            views.append(("barfocus", {k: v[keep] for k, v in full.items()}, False))

        for kind, d, allow_log in views:
            written += _panel(trace, metric, label, kind, d["names"],
                              d["means"], d["los"], d["his"], d["kinds"],
                              allow_log)
    return written


def _panel(trace, metric, label, kind, names, means, los, his,
           kinds, allow_log) -> list[Path]:
        use_log = allow_log and metric in LOG_METRICS and bool((means > 0).all())

        fig, ax = plt.subplots(figsize=(3.4, 2.6))
        x = np.arange(len(names))
        palette = {"drl": DRL_COLOR, "heuristic": BASE_COLOR,
                   "random": RAND_COLOR}
        colors = [palette[k] for k in kinds]
        # Heuristics are single deterministic runs and have no interval; the
        # DRL bars and the random control both do.
        has_ci = kinds != "heuristic"
        is_base = kinds == "heuristic"
        is_rand = kinds == "random"

        if use_log:
            # A log axis has no zero to grow a bar from, so anchor the bars half
            # a decade below the smallest value and draw floor -> mean.
            floor = 10.0 ** np.floor(np.log10(means.min()) - 0.5)
            heights = means - floor
            yerr = np.vstack([np.clip(means - los, 0, None),
                              np.clip(his - means, 0, None)])
        else:
            floor = 0.0
            heights = means
            yerr = np.vstack([means - los, his - means])

        ax.bar(x, heights, bottom=floor, color=colors, edgecolor="black",
               linewidth=0.5, width=0.7)
        ax.errorbar(x[has_ci], means[has_ci],
                    yerr=yerr[:, has_ci], fmt="none",
                    ecolor="black", elinewidth=0.8, capsize=2.5)

        # Heuristics as horizontal rules, so "does this DRL interval reach the
        # heuristic" is answerable without reading values off the axis. The
        # random control gets its own rule for the same reason -- it is the
        # floor, and whether a DRL bar clears it is the N27 question.
        for m in means[is_base]:
            ax.axhline(m, color=BASE_COLOR, linestyle="--", linewidth=0.7,
                       alpha=0.75, zorder=0)
        for m in means[is_rand]:
            ax.axhline(m, color=RAND_COLOR, linestyle=":", linewidth=0.9,
                       alpha=0.9, zorder=0)

        # Mark the overall best (lower is better except utilisation). Drawn as a
        # marker rather than a text glyph -- the serif stack has no star glyph.
        better_high = metric.endswith("utilization")
        target = means.max() if better_high else means.min()
        winners = [(xi, m) for xi, m in zip(x, means) if m == target]
        if winners:
            wx, wy = zip(*winners)
            offset = 1.35 if use_log else 1.06
            ax.plot(wx, np.asarray(wy) * offset, marker="*", linestyle="none",
                    markersize=7, color=ACCENT, clip_on=False, zorder=5)

        if use_log:
            ax.set_yscale("log")
            ax.set_ylim(bottom=floor)
        else:
            # Zoom to the data band so a few percent is actually visible; the
            # whole point of the focus panel.
            lo_b, hi_b = float(los.min()), float(his.max())
            pad = (hi_b - lo_b) * 0.35 or hi_b * 0.05
            ax.set_ylim(max(0.0, lo_b - pad), hi_b + pad)

        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=40, ha="right")
        ax.set_ylabel(label + (" (log)" if use_log else ""))
        ax.grid(axis="y", alpha=0.25, linewidth=0.5,
                which="both" if use_log else "major")
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)

        handles = [
            Patch(facecolor=DRL_COLOR, edgecolor="black", linewidth=0.5,
                  label="DRL (mean, 95% CI)"),
            Patch(facecolor=BASE_COLOR, edgecolor="black", linewidth=0.5,
                  label="Heuristic (deterministic)"),
        ]
        if is_rand.any():
            handles.append(Patch(facecolor=RAND_COLOR, edgecolor="black",
                                 linewidth=0.5,
                                 label="Random control (mean, 95% CI)"))
        ax.legend(handles=handles, loc="best", framealpha=0.9)

        FIG_DIR.mkdir(parents=True, exist_ok=True)
        written = []
        for ext in ("pdf", "png"):
            path = FIG_DIR / f"{trace}_{kind}_{metric}.{ext}"
            fig.savefig(path)
            written.append(path)
        plt.close(fig)
        return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trace", action="append", choices=sorted(TRACES),
                    help="draw only this trace (repeatable). Default: both. "
                         "Use while the other sweep is still running.")
    args = ap.parse_args()

    traces = ({t: TRACES[t] for t in args.trace} if args.trace else dict(TRACES))

    for trace, dirname in traces.items():
        written = draw(trace, dirname)
        pdfs = [p for p in written if p.suffix == ".pdf"]
        print(f"{trace}: wrote {len(pdfs)} figures "
              f"({', '.join(p.stem for p in pdfs)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
