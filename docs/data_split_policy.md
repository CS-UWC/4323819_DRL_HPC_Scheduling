# Time-Aware Data Split Policy

Status: locked for the v1 study release

Owner: Justin M. Cheney

Last updated: 2026-08-30

## Policy

- Stable-sort each source trace by `Submit`; never random-shuffle trace order.
- Use the earliest 70% for development, training, comparison, and selection.
- Reserve the latest 30% for final reporting only.
- Evaluate all six frozen DRL treatments on holdout across the configured seeds.
- Never tune, select, early-stop, or revise a treatment from holdout results.
- Optional blocked cross-validation is allowed only inside development data and was not used for the v1 release.

## Inputs and deterministic outputs

| Source | Total | Development | Holdout | Split ID |
|---|---:|---:|---:|---|
| `data/physical_job.csv` | 84,135 | 58,894 | 25,241 | `physical_job_r70` |
| `data/deeplearn_job.csv` | 68,720 | 48,104 | 20,616 | `deeplearn_job_r70` |

`src.make_split` writes:

```text
data/splits/<trace>_dev70.tsv
data/splits/<trace>_holdout30.tsv
data/splits/logs/<trace>_r70.json
```

The metadata includes the source path and SHA-256, ratio, sort key, row counts, stable split ID, timestamp, and output paths. The timestamp records when the split was generated; it is not part of `split_id`.

## Command

```bash
python -m src.make_split --src physical_job --ratio 0.7 --out-dir data/splits/
python -m src.make_split --src deeplearn_job --ratio 0.7 --out-dir data/splits/
```

## Leakage controls

1. Training rules pass only `*_dev70.tsv`.
2. `src.train_agents` rejects paths matching holdout/test patterns before environment construction.
3. Development summaries feed `src.select_best`.
4. Holdout rules run after the treatment definitions and seed matrix are frozen.
5. Holdout outputs feed final reporting only; no edge returns to training or selection in the DAG.

Any change to the split ratio, sort key, source bytes, or holdout scope creates a new experiment definition and must not overwrite v1 evidence.
