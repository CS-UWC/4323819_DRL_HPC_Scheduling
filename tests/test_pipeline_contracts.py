"""Regression checks for Phase 1 pipeline file contracts.

Run inside the Nix development shell because the pipeline modules import their
runtime dependencies at module load time.
"""

from __future__ import annotations

import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

# These contract tests do not train or load policies. Stub the heavyweight
# algorithm modules before importing src.utils so the file-seam checks can run
# without downloading the CUDA-enabled development environment.
ALGORITHM_STUBS = {
    "stable_baselines3": {"PPO": object, "DQN": object, "A2C": object},
    "sb3_contrib": {},
    "sb3_contrib.ppo_mask": {"MaskablePPO": object},
    "src.a2c_mask": {"MaskableA2C": object},
    "src.dqn_mask": {"MaskableDQN": object},
    "src.sb3_compat": {},
}
for module_name, attributes in ALGORITHM_STUBS.items():
    module = types.ModuleType(module_name)
    for name, value in attributes.items():
        setattr(module, name, value)
    sys.modules[module_name] = module

from src.HPCsim.HPCsim import HPCsim
from src.aggregate_results import main as aggregate_main
from src.select_best import main as select_best_main
from src.utils import MANIFEST_REQUIRED, load_split_metadata, write_manifest_entry

for module_name in ALGORITHM_STUBS:
    sys.modules.pop(module_name, None)


class PipelineContractTests(unittest.TestCase):
    def test_manifest_rerun_returns_one_canonical_row_and_rejects_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "runs.csv"
            kwargs = dict(
                treatment_id="ppo__mask_false", algorithm="ppo", use_masking=False,
                seed=7, window_size=512, tail_size=64, split_id="physical_job_dev70",
                model_path="model.zip", trace_file="data/splits/physical_job_dev70.tsv",
                topology_file="physical_topology.txt", node_file="nodes.csv", manifest_path=manifest,
            )
            self.assertEqual(write_manifest_entry(**kwargs), "ppo_001")
            self.assertEqual(write_manifest_entry(**kwargs), "ppo_001")
            self.assertEqual(len(pd.read_csv(manifest)), 1)
            with self.assertRaisesRegex(ValueError, "Conflicting manifest rows"):
                write_manifest_entry(**(kwargs | {"model_path": "other.zip"}))

    def test_split_metadata_requires_an_exact_split_id(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "physical_job_r70.json"
            log.write_text(json.dumps({"split_id": "physical_job_r70"}))
            self.assertEqual(
                load_split_metadata(directory, "physical_job_r70")["split_id"],
                "physical_job_r70",
            )
            with self.assertRaises(FileNotFoundError):
                load_split_metadata(directory, "physical_job_r7")

    def test_hpcsim_run_writes_to_explicit_path(self) -> None:
        class FakeQueue:
            job_queue = []

        class FakeEnv:
            event_queue = {}
            queue = FakeQueue()
            scheduler_factor = "fcfs"
            allocator_factor = "best_fit"

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "isolated" / "raw.csv"
            HPCsim.run(FakeEnv(), output)
            self.assertTrue(output.exists())
            self.assertEqual(pd.read_csv(output).columns.tolist(), [
                "time", "node_utilization", "cpu_utilization", "gpu_utilization", "mem_utilization",
            ])

    def test_aggregate_rejects_partial_unless_explicitly_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.csv"
            runs = root / "runs"
            runs.mkdir()
            row = {
                "run_id": "ppo_001", "treatment_id": "ppo__mask_false", "algorithm": "ppo",
                "use_masking": False, "seed": 7, "window_size": 512, "tail_size": 64,
                "split_id": "physical_job_dev70", "model_path": "model.zip",
                "trace_file": "data/splits/physical_job_dev70.tsv", "topology_file": "physical_topology.txt",
                "node_file": "nodes.csv",
            }
            pd.DataFrame([row], columns=MANIFEST_REQUIRED).to_csv(manifest, index=False)
            metrics = {
                **row, "episode_reward": 1.0, "decision_count": 5,
                "completed_job_count": 3, "decision_latency_mean_ms": 1.0, "eval_wall_s": 1.0,
                "evaluation_complete": False, "requested_max_steps": 5,
                "termination_reason": "step_cap", "max_waiting": 1.0, "avg_waiting": 1.0,
                "max_slowdown": 1.0, "avg_slowdown": 1.0, "avg_turnaround": 1.0,
                "cpu_utilization": 1.0, "gpu_utilization": 0.0,
            }
            pd.DataFrame([metrics]).to_csv(runs / "ppo_001_metrics.csv", index=False)
            args = ["aggregate_results", "--manifest", str(manifest), "--eval-root", str(runs),
                    "--output-dir", str(root / "aggregate"), "--no-strict"]
            with patch.object(sys, "argv", args), self.assertRaises(SystemExit):
                aggregate_main()
            with patch.object(sys, "argv", [*args, "--allow-partial"]):
                aggregate_main()
            self.assertTrue((root / "aggregate" / "eval_wide.csv").exists())

    def test_selector_honours_configured_metrics_and_writes_rationale(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            summary = root / "seed_summary.csv"
            pd.DataFrame([
                {"treatment_id": "a", "avg_waiting_mean": 1.0, "avg_slowdown_mean": 2.0,
                 "cpu_utilization_mean": 0.2},
                {"treatment_id": "b", "avg_waiting_mean": 2.0, "avg_slowdown_mean": 1.0,
                 "cpu_utilization_mean": 0.9},
            ]).to_csv(summary, index=False)
            with patch.object(sys, "argv", [
                "select_best", "--seed-summary", str(summary), "--output-dir", str(root),
                "--pareto-metrics", "cpu_utilization", "--tie-breakers", "avg_waiting",
            ]):
                select_best_main()
            result = json.loads((root / "best_algorithm.json").read_text())
            self.assertEqual(result["treatment_id"], "b")
            self.assertEqual(result["selection_rationale"]["pareto_metrics"], ["cpu_utilization"])


if __name__ == "__main__":
    unittest.main()
