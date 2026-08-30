#!/usr/bin/env python3
"""Validate the immutable files and experiment shape of results/v1."""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from pathlib import Path

EXPECTED_TREATMENTS = {
    "a2c__mask_false",
    "dqn__mask_false",
    "ppo__mask_false",
    "maskable_a2c__mask_true",
    "maskable_dqn__mask_true",
    "maskable_ppo__mask_true",
}
EXPECTED_SEEDS = {
    "16843", "20603", "21095", "21385", "35474",
    "45765", "57434", "170797", "210169", "250564",
}


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate_release(root: Path) -> None:
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    artifacts = manifest["artifacts"]
    declared = {item["path"] for item in artifacts}
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name not in {"README.md", "manifest.json"}
    }
    if declared != actual:
        raise ValueError(
            f"Manifest/file mismatch: missing={sorted(declared - actual)}, "
            f"undeclared={sorted(actual - declared)}"
        )

    for item in artifacts:
        path = root / item["path"]
        if path.stat().st_size != item["bytes"] or sha256(path) != item["sha256"]:
            raise ValueError(f"Hash or size mismatch: {item['path']}")
        if script_path := item.get("generation_script_path"):
            script = root / script_path
            if sha256(script) != item["generation_script_sha256"]:
                raise ValueError(f"Generation script mismatch: {item['path']}")

    for trace in ("physical", "deeplearn"):
        for scope in ("development", "holdout"):
            seed_path = root / "tables" / trace / scope / "seed_summary.csv"
            algorithm_path = root / "tables" / trace / scope / "algorithm_summary.csv"
            seeds = read_csv(seed_path)
            algorithms = read_csv(algorithm_path)
            if len(seeds) != 60 or len(algorithms) != 6:
                raise ValueError(f"Unexpected {trace}/{scope} row counts")
            expected_pairs = {
                (treatment, seed)
                for treatment in EXPECTED_TREATMENTS
                for seed in EXPECTED_SEEDS
            }
            actual_pairs = {(row["treatment_id"], row["seed"]) for row in seeds}
            if actual_pairs != expected_pairs:
                raise ValueError(f"Incomplete {trace}/{scope} treatment-seed grid")
            expected_split = f"{trace}_job_r70"
            for row in seeds:
                algorithm, mask = row["treatment_id"].split("__mask_")
                if (
                    row["algorithm"] != algorithm
                    or row["use_masking"].lower() != ("true" if mask == "true" else "false")
                    or row["split_id"] != expected_split
                ):
                    raise ValueError(f"Inconsistent {trace}/{scope} identity fields")


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("results/v1")
    validate_release(root)
    print(f"Validated {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
