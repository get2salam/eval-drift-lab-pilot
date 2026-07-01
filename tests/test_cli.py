"""Integration tests for the eval-drift CLI."""
import io
import json
import sys
import unittest
from pathlib import Path

from eval_drift.cli import main

FIXTURE_DIR = Path(__file__).parent / "fixtures"
BASELINE = str(FIXTURE_DIR / "baseline.json")
CANDIDATE_OK = str(FIXTURE_DIR / "candidate_ok.json")
CANDIDATE_DRIFTED = str(FIXTURE_DIR / "candidate_drifted.json")


class _CaptureStdout:
    """Context manager that captures sys.stdout into a StringIO buffer."""

    def __enter__(self):
        self._buf = io.StringIO()
        self._orig = sys.stdout
        sys.stdout = self._buf
        return self._buf

    def __exit__(self, *_):
        sys.stdout = self._orig


class _CaptureStderr:
    """Context manager that captures sys.stderr into a StringIO buffer."""

    def __enter__(self):
        self._buf = io.StringIO()
        self._orig = sys.stderr
        sys.stderr = self._buf
        return self._buf

    def __exit__(self, *_):
        sys.stderr = self._orig


class TestCLICompareExitCodes(unittest.TestCase):
    def test_exit_0_when_no_drift(self):
        with _CaptureStdout():
            code = main(["compare", BASELINE, CANDIDATE_OK])
        self.assertEqual(code, 0)

    def test_exit_1_when_drift(self):
        with _CaptureStdout():
            code = main(["compare", BASELINE, CANDIDATE_DRIFTED])
        self.assertEqual(code, 1)

    def test_custom_threshold_suppresses_drift(self):
        with _CaptureStdout():
            code = main(["compare", BASELINE, CANDIDATE_DRIFTED, "--threshold", "0.5"])
        self.assertEqual(code, 0)

    def test_metric_filter_no_drift(self):
        # f1 delta is tiny — filtering to f1 only should report no drift
        with _CaptureStdout():
            code = main(["compare", BASELINE, CANDIDATE_DRIFTED, "--metrics", "f1"])
        self.assertEqual(code, 0)

    def test_short_threshold_flag(self):
        with _CaptureStdout():
            code = main(["compare", BASELINE, CANDIDATE_DRIFTED, "-t", "0.5"])
        self.assertEqual(code, 0)


class TestCLICompareTextOutput(unittest.TestCase):
    def test_summary_output_contains_metric_table(self):
        with _CaptureStdout() as buf:
            main(["compare", BASELINE, CANDIDATE_OK])
        out = buf.getvalue()
        self.assertIn("Metric", out)
        self.assertIn("Baseline", out)
        self.assertIn("Candidate", out)
        self.assertIn("accuracy", out)

    def test_summary_contains_threshold_line(self):
        with _CaptureStdout() as buf:
            main(["compare", BASELINE, CANDIDATE_OK])
        self.assertIn("threshold", buf.getvalue())


class TestCLICompareJSONOutput(unittest.TestCase):
    def test_json_output_no_drift(self):
        with _CaptureStdout() as buf:
            code = main(["compare", BASELINE, CANDIDATE_OK, "--json"])
        self.assertEqual(code, 0)
        data = json.loads(buf.getvalue())
        self.assertFalse(data["has_drift"])
        self.assertIn("results", data)
        self.assertIn("threshold", data)

    def test_json_output_with_drift(self):
        with _CaptureStdout() as buf:
            code = main(["compare", BASELINE, CANDIDATE_DRIFTED, "--json"])
        self.assertEqual(code, 1)
        data = json.loads(buf.getvalue())
        self.assertTrue(data["has_drift"])

    def test_json_output_result_fields(self):
        with _CaptureStdout() as buf:
            main(["compare", BASELINE, CANDIDATE_OK, "--json"])
        data = json.loads(buf.getvalue())
        for result in data["results"]:
            self.assertIn("metric", result)
            self.assertIn("baseline", result)
            self.assertIn("candidate", result)
            self.assertIn("delta", result)
            self.assertIn("drifted", result)

    def test_short_json_flag(self):
        with _CaptureStdout() as buf:
            main(["compare", BASELINE, CANDIDATE_OK, "-j"])
        data = json.loads(buf.getvalue())
        self.assertIsInstance(data, dict)


class TestCLIErrors(unittest.TestCase):
    def test_missing_baseline_exits_2(self):
        with _CaptureStdout(), _CaptureStderr() as err:
            code = main(["compare", "/nonexistent_baseline.json", CANDIDATE_OK])
        self.assertEqual(code, 2)
        self.assertIn("not found", err.getvalue())

    def test_missing_candidate_exits_2(self):
        with _CaptureStdout(), _CaptureStderr() as err:
            code = main(["compare", BASELINE, "/nonexistent_candidate.json"])
        self.assertEqual(code, 2)
        self.assertIn("not found", err.getvalue())

    def test_missing_baseline_names_path_in_error(self):
        with _CaptureStdout(), _CaptureStderr() as err:
            main(["compare", "/no_such_file.json", CANDIDATE_OK])
        self.assertIn("/no_such_file.json", err.getvalue())

    def test_unknown_metric_warns_to_stderr(self):
        with _CaptureStdout(), _CaptureStderr() as err:
            main(["compare", BASELINE, CANDIDATE_OK, "--metrics", "ghost_metric"])
        self.assertIn("ghost_metric", err.getvalue())

    def test_all_unknown_metrics_exits_2(self):
        with _CaptureStdout(), _CaptureStderr() as err:
            code = main(["compare", BASELINE, CANDIDATE_OK, "--metrics", "ghost_metric"])
        self.assertEqual(code, 2)
        self.assertIn("no metrics were compared", err.getvalue())
