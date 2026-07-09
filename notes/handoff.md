# Handoff — sweep execution & debugging state

*Operational handoff for a fresh agent/chat. Last updated 2026-07-09.*
*For the **why** behind each fix, see the paper-facing notes referenced below; this
doc is only the current state, the constraints, and the open decisions.*

---

## What this project is

`herasched`: a DRL HPC scheduler study. Full SLURM sweep = **10 seeds × 6
algorithms** (`ppo, a2c, dqn` + `maskable_ppo, maskable_a2c, maskable_dqn`), 3M
train steps each, evaluated on `dev70`, winner re-evaluated on `holdout30`, compared
against traditional baselines, then a statistical pipeline. Orchestrated by
`Snakefile` via Snakemake + the SLURM executor (`profiles/slurm/`), one job per
`(seed × algo)`.

Cluster: partition `main`, **10 nodes, 128 GB RAM / 24 cores each; only 4 of the 10
have an L4 GPU** (the other 6 are CPU-only), and in practice only **~2-3 of those GPU
nodes are free** (shared with other projects). `train_agent` requests `gres=gpu:1`, so
training can run **only on the GPU nodes** (≤2-4 concurrent) — the 6 CPU-only nodes
idle during training unless a CPU-only rule (e.g. CPU eval) is scheduled on them.
Partition wall-clock limit is **14 h** (840 min) — a hard ceiling; jobs slower than
that cannot complete (no resume). `just` drives everything (`just run_full_slurm`,
`just clean_all`, etc.).

## Hard constraints (do not violate)

1. **`src/HPCsim/` is READ-ONLY.** Reading fine; never edit. All env-side changes go
   through wrappers (e.g. `src/obs_wrapper.py`).
2. **Dual-repo mirroring.** Every change is applied to BOTH:
   - `github_repos/herasched/` — the git repo (no `docs/` dir).
   - `Project_Github/` (cluster mirror at `~/DRL_HPC_Scheduling`) — has a `docs/` dir.
   Keep source/notes/scripts identical across the two.
3. **Snakefile baseline-rule drift is intentional.** The two `Snakefile`s differ ONLY
   at the `baseline` rule (~line 526: Project_Github has a trailing `&` + a `wait`;
   herasched does not). Do NOT "fix" this — verify `diff` shows *only* that hunk after
   any Snakefile edit.
4. **Keep Wang et al. (2025) `[4096,2048,1024]` net architecture** (fidelity). Do not
   shrink it as a speed shortcut without an explicit decision.
5. **Don't start changes without confirmation.**

## Snakemake mechanics worth knowing

- **`code` rerun-trigger hashes only a rule's `shell:` block, not imported `.py`.**
  Editing `src/train_agents.py` / `src/a2c_mask.py` / etc. does NOT auto-trigger
  reruns. Force reruns by deleting the target outputs (see `clean_algo.sh`).
- **Manifest `logs/run_log.csv` is append-only** (`write_manifest_entry`,
  `utils.py`). run_id = `{algo}_{NNN}`, auto-numbered. Rerunning a *completed* job
  appends a DUPLICATE row → breaks aggregate's run_id uniqueness. Rerunning a
  *failed/timed-out* job is clean (it never wrote a row — the write happens only
  after `model.save`).
- **Aggregate is manifest-driven**: only run_ids present in the manifest are read;
  stale files are ignored, duplicate rows break it.
- Queued-but-not-started SLURM jobs pick up **new code** (read from the shared FS at
  job start) but **old resources** (`--time`/`--mem`/`--gres` are baked at `sbatch`).

## Fixes already applied this arc (all in both repos)

Rationale for each is in the referenced note.

| Area | Change | Where | Note |
|---|---|---|---|
| Obs memory | float32 observation wrapper (global) | `src/obs_wrapper.py` + both env paths | `obs_wrapper.md` |
| DQN OOM | `buffer_size=150_000`; per-algo `mem_mb`/`cpus` | `config.yaml`, `Snakefile` | `training_performance.md`, `process_notes_for_paper.md` |
| Checkpoints | `save_interval=300000`, `total_saving=10`; prune all but final | `config.yaml`, train code | `process_notes_for_paper.md` |
| A2C wall-clock | train `runtime=720` | `Snakefile train_agent` | `process_notes_for_paper.md` |
| A2C NaN blow-up | `ent_coef=0.01` (build_model, experiment choice) **+** `normalize_advantage` default `True→False` (corrected at source in `a2c_mask.py`, canonical A2C) | `src/train_agents.py`, `src/a2c_mask.py` | `process_notes_for_paper.md` |
| Eval empty-log | steps/s heartbeat every 2k steps + `PYTHONUNBUFFERED=1` | `src/evaluate_agents.py`, `Snakefile` | `process_notes_for_paper.md` |
| **Eval speed** | Heartbeats showed PPO 34.6 vs DQN 18 steps/s on the *same* env ⇒ forward-pass-bound (230M-param first layer, ~920 MB/step, bandwidth-bound on CPU), NOT env-bound. `runtime` raised `480→840` (14 h max). **HYBRID gres** in `eval_run`: `gpu:1` only for the DQN family (`gres=lambda wildcards: "gpu:1" if "dqn" in wildcards.algo else ""` — plugin v2.7.1 skips a falsy gres), CPU for PPO/A2C + maskables so they use the CPU nodes and don't fight for the ~2-3 shared GPUs. `holdout_eval` keeps `gpu:1` (winner algo unknown at DAG-build, only 10 jobs). Heartbeat also logs jobs-completed + running avg_wait/avg_slowdown. Note: eval = ONE full deterministic episode over the eval trace (loop `while not done/truncated`, `eval_max_steps: null`), NOT the 3M *training* budget; ~1M+ steps is the dev70 replay length, varies per policy. | `Snakefile`, `src/evaluate_agents.py` | `process_notes_for_paper.md` |

## Tooling added

- **`scripts/clean_algo.sh <algo>`** — wipes ONE algorithm's models, `.train_complete`
  markers, eval completion markers, metric/metadata sidecars, per-job snakemake logs,
  AND its `run_log.csv` rows, so `just run_full_slurm` retrains + re-evaluates only it
  without duplicate manifest rows. Snakemake then cascades aggregate/stats/holdout.
  Exact per-algo match (`a2c` never touches `maskable_a2c`). `DRYRUN=1` previews.
  `TRACE_NAME=` overrides the trace (default `physical_job`).

## Standard rerun workflow

1. `git push` from herasched (after applying + mirroring changes).
2. On the cluster: `scancel` any stuck/doomed jobs (e.g. `srun ... Requested nodes are
   busy` jobs heading for timeout); let the controller drain.
3. `git pull` in `Project_Github`.
4. Per algorithm being redone: `scripts/clean_algo.sh <algo>` (only needed to redo a
   *completed* algo; pure failures rerun on their own).
5. `just run_full_slurm` — reruns only jobs missing their output markers.

## OPEN DECISIONS / next steps

1. **maskable_a2c reruns:** `normalize_advantage=False` *materially* changes
   maskable_a2c (unlike the tiny `ent_coef` bump), so **all 10 maskable_a2c seeds
   should be re-run**, not just the crashed one. Stock `a2c` only got the minor
   `ent_coef` change (its `normalize_advantage` was already False in SB3). PPO/DQN
   unaffected. Use `scripts/clean_algo.sh maskable_a2c`.
1b. **LEADING PLAN — cap eval length by metric convergence (may make 2 moot).** Rather
   than fight the 14 h wall with hardware, cut the *work*: eval currently runs the full
   ~1M+ step episode, but the primary metrics (`avg_waiting`, `avg_slowdown`) are running
   means that likely converge long before the trace ends. Plan: (i) `evaluate_agents.py`
   heartbeat now also logs `jobs`-completed + running `avg_wait`/`avg_slowdown` (done,
   read-only) so one full run shows the convergence curve; (ii) from that curve pick a
   cap where the means are within ~±1% of final, past the warm-up transient, with margin;
   (iii) implement the cap **by jobs-completed or sim-time, NOT decision steps** (steps/job
   is policy-dependent → a step cap is unfair/incomparable across algos). Caveats to
   document: warm-up bias (early jobs see an empty system), and `max_waiting`/`max_slowdown`
   are running maxima so truncation biases them down (keep full-trace or caveat them).
   If a defensible cap lands well under 14 h for every algo, revert eval to CPU-for-all
   (all 10 nodes, overlaps training on the 6 CPU nodes) and decision 2 disappears. NOTE:
   full-trace eval is the most reviewer-proof option; a cap needs the convergence evidence
   + methodology writeup to defend.
2. **Eval placement — RESOLVED: hybrid (implemented).** `eval_run` sends the DQN
   family to GPU and everything else to CPU (see the Eval-speed row). Remaining
   watch item: confirm the **CPU algos (PPO/A2C + maskables) actually finish
   full-trace within the 14 h wall** — the first completed run of each proves it. If
   one grazes the ceiling, widen the gres predicate to send it to GPU too (or fall
   back to the capping plan, 1b). The 14 h limit is a hard wall (no eval resume).
3. **Confirm total episode step count (per algo):** inferred ~1M+ from heartbeats but
   no eval had hit `[OK]` yet, and it varies by policy. Grab the final step count from
   the first completed eval of each algo — this decides whether DQN actually exceeds
   14 h on CPU (i.e. whether it *must* have a GPU) and right-sizes `runtime`.

## Key files

- `Snakefile` — DAG; rules `train_agent`, `eval_run`, `holdout_eval`, `aggregate`,
  `stats`, `select_best`, `baseline*`, `visualise`.
- `src/train_agents.py` (`build_model` ~L370), `src/evaluate_agents.py`
  (`evaluate_one_run` single-env loop + heartbeat ~L188), `src/a2c_mask.py`
  (custom MaskableA2C), `src/utils.py` (`ALGORITHMS`, manifest, `resolve_algorithm_config`).
- `config.yaml` (`trace_name: physical_job`), `profiles/slurm/config.yaml`
  (`jobs:100`, defaults `mem_mb=8192 runtime=120 cpus=4`, `rerun-incomplete: true`).
- Splits: `data/splits/physical_job_dev70.tsv` (~59k jobs),
  `data/splits/physical_job_holdout30.tsv` (~25k).
- Notes: `process_notes_for_paper.md`, `obs_wrapper.md`, `training_performance.md`,
  `cur_prog.md` (pre-sweep pipeline/stats summary, dated 2026-07-04 — stale for the
  sweep arc but still the reference for the statistical pipeline & known stat bugs).
