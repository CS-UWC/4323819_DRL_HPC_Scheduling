from pathlib import Path
import unittest

from scripts.validate_results_release import validate_release


class ResultsReleaseTests(unittest.TestCase):
    def test_v1_manifest_and_experiment_shape(self) -> None:
        validate_release(Path("results/v1"))


if __name__ == "__main__":
    unittest.main()
