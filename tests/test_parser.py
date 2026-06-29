"""Tests for the JSON eval-run parser."""
import json
import tempfile
import unittest
from pathlib import Path

from eval_drift.parser import EvalRun

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class TestEvalRunFromDict(unittest.TestCase):
    def _valid(self) -> dict:
        return {
            "run_id": "test-run",
            "model": "test-model",
            "dataset": "test-dataset",
            "timestamp": "2024-01-01T00:00:00Z",
            "metrics": {"accuracy": 0.9, "f1": 0.85},
        }

    def test_parses_valid_dict(self):
        run = EvalRun.from_dict(self._valid())
        self.assertEqual(run.run_id, "test-run")
        self.assertEqual(run.model, "test-model")
        self.assertAlmostEqual(run.metrics["accuracy"], 0.9)

    def test_raises_on_missing_field(self):
        data = self._valid()
        del data["metrics"]
        with self.assertRaises(ValueError):
            EvalRun.from_dict(data)

    def test_raises_on_non_dict_metrics(self):
        data = self._valid()
        data["metrics"] = [0.9, 0.85]
        with self.assertRaises(TypeError):
            EvalRun.from_dict(data)

    def test_raises_on_non_numeric_metric(self):
        data = self._valid()
        data["metrics"]["accuracy"] = "high"
        with self.assertRaises(TypeError):
            EvalRun.from_dict(data)

    def test_integer_metrics_coerced_to_float(self):
        data = self._valid()
        data["metrics"]["count"] = 42
        run = EvalRun.from_dict(data)
        self.assertIsInstance(run.metrics["count"], float)
        self.assertAlmostEqual(run.metrics["count"], 42.0)

    def test_extra_fields_stored_in_metadata(self):
        data = self._valid()
        data["notes"] = "experiment A"
        run = EvalRun.from_dict(data)
        self.assertEqual(run.metadata.get("notes"), "experiment A")

    def test_multiple_missing_fields_all_reported(self):
        with self.assertRaises(ValueError) as ctx:
            EvalRun.from_dict({})
        self.assertIn("Missing", str(ctx.exception))


class TestEvalRunFromFile(unittest.TestCase):
    def test_loads_baseline_fixture(self):
        run = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
        self.assertEqual(run.run_id, "run-2024-06-01")
        self.assertIn("accuracy", run.metrics)
        self.assertIn("f1", run.metrics)

    def test_loads_candidate_ok_fixture(self):
        run = EvalRun.from_file(FIXTURE_DIR / "candidate_ok.json")
        self.assertEqual(run.run_id, "run-2024-06-08")

    def test_loads_candidate_drifted_fixture(self):
        run = EvalRun.from_file(FIXTURE_DIR / "candidate_drifted.json")
        self.assertEqual(run.run_id, "run-2024-06-15")

    def test_raises_on_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            EvalRun.from_file("/nonexistent/path/run.json")

    def test_roundtrip_via_temp_file(self):
        original = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
        data = {
            "run_id": original.run_id,
            "model": original.model,
            "dataset": original.dataset,
            "timestamp": original.timestamp,
            "metrics": original.metrics,
        }
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as f:
            json.dump(data, f)
            tmp = f.name
        try:
            loaded = EvalRun.from_file(tmp)
            self.assertEqual(loaded.run_id, original.run_id)
            self.assertEqual(loaded.metrics, original.metrics)
        finally:
            Path(tmp).unlink(missing_ok=True)
