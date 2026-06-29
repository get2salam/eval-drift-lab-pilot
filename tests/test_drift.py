"""Tests for the drift comparison engine."""
import unittest
from pathlib import Path

from eval_drift.drift import DriftReport, MetricResult, compare
from eval_drift.parser import EvalRun

FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _run(run_id: str, metrics: dict) -> EvalRun:
    return EvalRun(
        run_id=run_id,
        model="model-a",
        dataset="ds-v1",
        timestamp="2024-01-01T00:00:00Z",
        metrics=metrics,
    )


class TestCompareIdenticalRuns(unittest.TestCase):
    def setUp(self):
        self.baseline = _run("base", {"accuracy": 0.80, "f1": 0.75})
        self.candidate = _run("cand", {"accuracy": 0.80, "f1": 0.75})

    def test_no_drift_when_equal(self):
        report = compare(self.baseline, self.candidate)
        self.assertFalse(report.has_drift)
        self.assertEqual(len(report.drifted_metrics), 0)

    def test_result_count_matches_metrics(self):
        report = compare(self.baseline, self.candidate)
        self.assertEqual(len(report.results), 2)

    def test_delta_is_zero(self):
        report = compare(self.baseline, self.candidate)
        for r in report.results:
            self.assertAlmostEqual(r.delta, 0.0)


class TestCompareWithDrift(unittest.TestCase):
    def setUp(self):
        self.baseline = _run("base", {"accuracy": 0.80, "f1": 0.75, "recall": 0.70})
        self.candidate = _run("cand", {"accuracy": 0.70, "f1": 0.74, "recall": 0.70})

    def test_detects_accuracy_drift(self):
        report = compare(self.baseline, self.candidate, threshold=0.05)
        drifted_names = {r.name for r in report.drifted_metrics}
        self.assertIn("accuracy", drifted_names)

    def test_no_drift_within_threshold(self):
        report = compare(self.baseline, self.candidate, threshold=0.05)
        ok_names = {r.name for r in report.results if not r.drifted}
        self.assertIn("f1", ok_names)
        self.assertIn("recall", ok_names)

    def test_has_drift_flag_true(self):
        report = compare(self.baseline, self.candidate, threshold=0.05)
        self.assertTrue(report.has_drift)

    def test_delta_calculation(self):
        report = compare(self.baseline, self.candidate, threshold=0.05)
        acc = next(r for r in report.results if r.name == "accuracy")
        self.assertAlmostEqual(acc.delta, -0.10, places=6)

    def test_custom_threshold_suppresses_drift(self):
        report = compare(self.baseline, self.candidate, threshold=0.15)
        self.assertFalse(report.has_drift)

    def test_metric_filter_limits_results(self):
        report = compare(self.baseline, self.candidate, metrics=["accuracy"])
        self.assertEqual(len(report.results), 1)
        self.assertEqual(report.results[0].name, "accuracy")

    def test_metric_filter_excludes_drifted(self):
        report = compare(self.baseline, self.candidate, metrics=["f1"])
        self.assertFalse(report.has_drift)

    def test_metrics_sorted_alphabetically_by_default(self):
        report = compare(self.baseline, self.candidate)
        names = [r.name for r in report.results]
        self.assertEqual(names, sorted(names))

    def test_report_contains_correct_ids(self):
        report = compare(self.baseline, self.candidate)
        self.assertEqual(report.baseline_id, "base")
        self.assertEqual(report.candidate_id, "cand")


class TestCompareFixtures(unittest.TestCase):
    def test_no_drift_with_ok_candidate(self):
        baseline = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
        candidate = EvalRun.from_file(FIXTURE_DIR / "candidate_ok.json")
        report = compare(baseline, candidate, threshold=0.05)
        self.assertFalse(report.has_drift)

    def test_drift_with_drifted_candidate(self):
        baseline = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
        candidate = EvalRun.from_file(FIXTURE_DIR / "candidate_drifted.json")
        report = compare(baseline, candidate, threshold=0.05)
        self.assertTrue(report.has_drift)

    def test_drifted_metrics_are_accuracy_and_precision(self):
        baseline = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
        candidate = EvalRun.from_file(FIXTURE_DIR / "candidate_drifted.json")
        report = compare(baseline, candidate, threshold=0.05)
        drifted = {r.name for r in report.drifted_metrics}
        self.assertIn("accuracy", drifted)
        self.assertIn("precision", drifted)

    def test_summary_contains_run_ids(self):
        baseline = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
        candidate = EvalRun.from_file(FIXTURE_DIR / "candidate_drifted.json")
        report = compare(baseline, candidate)
        summary = report.summary()
        self.assertIn("run-2024-06-01", summary)
        self.assertIn("run-2024-06-15", summary)

    def test_summary_contains_drift_status(self):
        baseline = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
        candidate = EvalRun.from_file(FIXTURE_DIR / "candidate_drifted.json")
        report = compare(baseline, candidate)
        summary = report.summary()
        self.assertIn("DRIFT DETECTED", summary)

    def test_summary_clean_when_no_drift(self):
        baseline = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
        candidate = EvalRun.from_file(FIXTURE_DIR / "candidate_ok.json")
        report = compare(baseline, candidate)
        summary = report.summary()
        self.assertIn("CLEAN", summary)

    def test_all_four_metrics_compared(self):
        baseline = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
        candidate = EvalRun.from_file(FIXTURE_DIR / "candidate_ok.json")
        report = compare(baseline, candidate)
        self.assertEqual(len(report.results), 4)
