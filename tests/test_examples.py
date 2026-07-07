"""Guard test for examples/ — keeps the runnable docs example from rotting."""
import subprocess
import sys
import unittest
from pathlib import Path

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"


class TestDetectRenamedMetricsExample(unittest.TestCase):
    def _run(self):
        return subprocess.run(
            [sys.executable, str(EXAMPLES_DIR / "detect_renamed_metrics.py")],
            capture_output=True,
            text=True,
        )

    def test_exits_1_when_a_metric_was_renamed(self):
        result = self._run()
        self.assertEqual(result.returncode, 1)

    def test_flags_both_old_and_new_metric_names(self):
        result = self._run()
        self.assertIn("recall", result.stdout)
        self.assertIn("recall_score", result.stdout)

    def test_report_above_only_scores_the_three_common_metrics(self):
        result = self._run()
        self.assertIn("Drifted metrics: 0 / 3", result.stdout)
