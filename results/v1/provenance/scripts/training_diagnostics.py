#!/usr/bin/env python3
"""training_diagnostics.py

Extract training-time diagnostics from the TensorBoard event files pulled off the
cluster (Project_Github/tb_logs/), and answer one question the results tables
cannot: was the 3M-timestep budget the binding constraint?

Why ep_rew_mean cannot answer it
--------------------------------
notes/process_notes_for_paper.md proposes reading `rollout/ep_rew_mean`'s slope
over 2M->3M -- still rising means the budget helps, flat means it does not. The
logs show that signal is **unusable here**: an episode is ~1M+ decision steps, so
only a handful complete within 3M timesteps and SB3's rolling `ep_info_buffer`
almost never refreshes. Across ~37 logged points a run typically reports **one or
two distinct reward values**. The curve is flat by construction, not by
convergence, and reading convergence off it would be an artifact.

This script measures that directly (`rew_distinct`) so the claim is evidenced
rather than asserted, and then falls back on the per-update signals, which are
recomputed at every gradient step and are therefore trustworthy:

  train/learning_rate       confirms the linear decay to ~0 by the horizon
  train/entropy_loss        SB3 logs NEGATIVE entropy; -1.5 means 1.5 nats left
  train/explained_variance  critic fit; <=0 means the value function explains
                            nothing -- the bottleneck is the value function, not
                            the number of steps

Usage:
    python3 scripts/training_diagnostics.py            # write tables + figure
    python3 scripts/training_diagnostics.py --summary  # print, write nothing
"""

from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator

PAPER_DIR = Path(__file__).resolve().parent.parent
TB_ROOT = PAPER_DIR.parent / "Project_Github" / "tb_logs"
OUT_DIR = PAPER_DIR / "data" / "results"
FIG_DIR = PAPER_DIR / "figures" / "results"

TRACES = {"physical": "physical_job", "deeplearn": "deeplearn_job"}

SWEEP_SEEDS = [16843, 20603, 21095, 21385, 35474, 45765, 57434,
               170797, 210169, 250564]

PRETTY = {
    "maskable_ppo": "MaskablePPO", "maskable_dqn": "MaskableDQN",
    "maskable_a2c": "MaskableA2C", "ppo": "PPO", "dqn": "DQN", "a2c": "A2C",
}
ALGO_ORDER = ["maskable_ppo", "maskable_dqn", "maskable_a2c", "ppo", "dqn", "a2c"]

# This script owns {trace}_training.csv and the explained-variance figures, so
# the truncation dagger has to be applied here as well as in
# build_results_data.py -- otherwise a rebuild silently drops it from these.
# Mathtext in the figure legend, a literal in the CSV that typst renders.
UNMASKED = {"ppo", "dqn", "a2c"}


def pretty(algo: str, mathtext: bool = False) -> str:
    name = PRETTY[algo]
    if algo not in UNMASKED:
        return name
    return name + ("$^\\dagger$" if mathtext else "†")

LATE = 2_000_000          # start of the "late training" window
BEST = "**{}**"

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Linux Libertine O", "Linux Libertine", "DejaVu Serif"],
    "font.size": 8, "axes.labelsize": 8, "axes.titlesize": 9,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "legend.fontsize": 7,
    "figure.dpi": 200, "savefig.bbox": "tight",
})


def merged_scalars(run_dir: Path, tag: str) -> tuple[np.ndarray, np.ndarray]:
    """Merge every event file in a run directory into one step->value series.

    A run that was restarted writes several event files, each covering part of
    the horizon. Reading only one (the naive glob) silently truncates the curve,
    so all files are merged and later writes win on duplicate steps.
    """
    pts: dict[int, float] = {}
    for f in sorted(run_dir.glob("events.out.tfevents.*")):
        ea = EventAccumulator(str(f), size_guidance={"scalars": 0})
        try:
            ea.Reload()
        except Exception:
            continue                      # truncated file from a killed job
        if tag not in ea.Tags()["scalars"]:
            continue
        for s in ea.Scalars(tag):
            pts[s.step] = s.value
    if not pts:
        return np.array([]), np.array([])
    steps = np.array(sorted(pts))
    return steps, np.array([pts[s] for s in steps])


def find_run(trace_dir: str, seed: int, algo: str) -> Path | None:
    # SB3 appends a run counter, so the directory is <algo>_<n>.
    hits = sorted(glob.glob(str(TB_ROOT / trace_dir / str(seed) / f"{algo}_*")))
    # "a2c_1" must not match a request for "a2c" when "maskable_a2c_1" exists,
    # and vice versa -- compare the stem exactly.
    exact = [h for h in hits if Path(h).name.rsplit("_", 1)[0] == algo]
    return Path(exact[0]) if exact else None


def late_stat(steps: np.ndarray, vals: np.ndarray) -> dict:
    if len(steps) == 0:
        return {"final": np.nan, "late_mean": np.nan, "late_band": np.nan, "n": 0}
    late = steps >= LATE
    sub = vals[late] if late.sum() else vals
    return {
        "final": float(vals[-1]),
        "late_mean": float(sub.mean()),
        "late_band": float(sub.max() - sub.min()) if len(sub) > 1 else 0.0,
        "n": int(len(steps)),
    }


def collect() -> pd.DataFrame:
    rows = []
    for trace, trace_dir in TRACES.items():
        for algo in ALGO_ORDER:
            for seed in SWEEP_SEEDS:
                run = find_run(trace_dir, seed, algo)
                if run is None:
                    continue
                rec = {"trace": trace, "algorithm": algo, "seed": seed}

                st, v = merged_scalars(run, "rollout/ep_rew_mean")
                rec["rew_points"] = len(v)
                # The diagnostic that matters: how many DISTINCT reward values
                # were ever logged. 1-2 means the buffer never refreshed.
                rec["rew_distinct"] = int(len(np.unique(np.round(v, 6)))) if len(v) else 0
                rec["rew_final"] = float(v[-1]) if len(v) else np.nan

                for tag, key in [("train/explained_variance", "ev"),
                                 ("train/entropy_loss", "ent"),
                                 ("train/learning_rate", "lr")]:
                    s, val = merged_scalars(run, tag)
                    for k, x in late_stat(s, val).items():
                        rec[f"{key}_{k}"] = x

                s, val = merged_scalars(run, "time/fps")
                rec["fps"] = float(np.median(val)) if len(val) else np.nan
                rec["max_step"] = int(s[-1]) if len(s) else 0
                rows.append(rec)
    return pd.DataFrame(rows)


def build_table(df: pd.DataFrame, trace: str) -> pd.DataFrame:
    """Per-algorithm diagnostics, aggregated across seeds."""
    sub = df[df["trace"] == trace]
    rows = []
    for algo in ALGO_ORDER:
        g = sub[sub["algorithm"] == algo]
        if g.empty:
            continue
        rows.append({
            "Algorithm": pretty(algo),
            "Seeds": str(len(g)),
            "Explained var. (final)": f"{g['ev_final'].mean():.3f} ± {g['ev_final'].std():.3f}"
                if g["ev_final"].notna().any() else "---",
            "Entropy (final, nats)": f"{-g['ent_final'].mean():.2f} ± {g['ent_final'].std():.2f}"
                if g["ent_final"].notna().any() else "---",
            "LR (final)": f"{g['lr_final'].mean():.1e}"
                if g["lr_final"].notna().any() else "---",
            "Reward pts / distinct": f"{g['rew_points'].mean():.0f} / {g['rew_distinct'].mean():.1f}",
        })
    out = pd.DataFrame(rows)
    # Best critic fit wins the explained-variance column.
    vals = []
    for algo in ALGO_ORDER:
        g = sub[sub["algorithm"] == algo]
        vals.append(g["ev_final"].mean() if not g.empty else np.nan)
    vals = [v for v in vals if not np.isnan(v)]
    if vals:
        target = max(vals)
        col = "Explained var. (final)"
        for i, algo in enumerate([a for a in ALGO_ORDER
                                  if not sub[sub["algorithm"] == a].empty]):
            g = sub[sub["algorithm"] == algo]
            if np.isclose(g["ev_final"].mean(), target):
                out.loc[i, col] = BEST.format(out.loc[i, col])
    return out


def draw_curves(df: pd.DataFrame) -> list[Path]:
    """Explained variance over training for the two competitive on-policy families.

    This is the figure that carries the budget argument: if the critic is flat at
    zero, more environment steps are not the missing ingredient.
    """
    written = []
    for trace, trace_dir in TRACES.items():
        fig, ax = plt.subplots(figsize=(3.4, 2.4))
        # A2C is plotted because it carries the paper's central diagnostic claim:
        # after the ent_coef removal it reaches the best critic fit in the study
        # (physical explained variance 0.968) and still does not beat the random
        # control. Omitting it left that argument without a figure. The DQN family
        # logs no explained_variance at all, so the panel is these four.
        for algo, color in [("maskable_ppo", "#4C72B0"), ("maskable_a2c", "#DD8452"),
                            ("ppo", "#55A868"), ("a2c", "#C44E52")]:
            curves = []
            for seed in SWEEP_SEEDS:
                run = find_run(trace_dir, seed, algo)
                if run is None:
                    continue
                s, v = merged_scalars(run, "train/explained_variance")
                if len(s) > 5:
                    curves.append((s, v))
            if not curves:
                continue
            grid = np.linspace(0, 3_000_000, 120)
            stack = np.vstack([np.interp(grid, s, v) for s, v in curves])
            med = np.median(stack, axis=0)
            ax.plot(grid / 1e6, med, color=color, linewidth=1.2,
                    label=pretty(algo, mathtext=True))
            ax.fill_between(grid / 1e6,
                            np.percentile(stack, 25, axis=0),
                            np.percentile(stack, 75, axis=0),
                            color=color, alpha=0.18, linewidth=0)

        ax.axhline(0, color="black", linewidth=0.6, linestyle=":")
        ax.set_xlabel("Training timesteps (millions)")
        ax.set_ylabel("Explained variance")
        ax.set_ylim(-0.6, 1.05)
        ax.grid(alpha=0.25, linewidth=0.5)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        ax.legend(loc="best", framealpha=0.9)

        FIG_DIR.mkdir(parents=True, exist_ok=True)
        for ext in ("pdf", "png"):
            p = FIG_DIR / f"{trace}_explained_variance.{ext}"
            fig.savefig(p)
            written.append(p)
        plt.close(fig)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--summary", action="store_true",
                    help="print findings, write nothing")
    args = ap.parse_args()

    if not TB_ROOT.exists():
        print(f"error: tb_logs not found at {TB_ROOT}", file=sys.stderr)
        return 2

    df = collect()
    if df.empty:
        print("error: no runs found", file=sys.stderr)
        return 2

    print(f"parsed {len(df)} runs "
          f"({df['trace'].nunique()} traces x {df['algorithm'].nunique()} algorithms)\n")

    print("ep_rew_mean usability — distinct values logged per run:")
    for trace in TRACES:
        s = df[df["trace"] == trace]
        print(f"  {trace:10s} median distinct = {s['rew_distinct'].median():.0f} "
              f"over a median of {s['rew_points'].median():.0f} logged points "
              f"({(s['rew_distinct'] <= 2).mean():.0%} of runs have <= 2)")

    print("\nfinal explained variance (mean over seeds):")
    for trace in TRACES:
        s = df[df["trace"] == trace]
        for algo in ALGO_ORDER:
            g = s[s["algorithm"] == algo]
            if g.empty or g["ev_final"].isna().all():
                continue
            print(f"  {trace:10s} {PRETTY[algo]:13s} "
                  f"{g['ev_final'].mean():+.3f} ± {g['ev_final'].std():.3f}  "
                  f"(n={g['ev_final'].notna().sum()})")

    if args.summary:
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_DIR / "training_diagnostics_raw.csv", index=False)
    for trace in TRACES:
        t = build_table(df, trace)
        t.to_csv(OUT_DIR / f"{trace}_training.csv", index=False)
        print(f"\nwrote data/results/{trace}_training.csv ({len(t)} rows)")
    for p in draw_curves(df):
        if p.suffix == ".pdf":
            print(f"wrote figures/results/{p.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
