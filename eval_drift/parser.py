"""Parse JSON model-evaluation run files into EvalRun objects."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class EvalRun:
    """Represents a single model-evaluation run loaded from a JSON file."""

    run_id: str
    model: str
    dataset: str
    timestamp: str
    metrics: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EvalRun":
        _required = ("run_id", "model", "dataset", "timestamp", "metrics")
        missing = [k for k in _required if k not in data]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        metrics = data["metrics"]
        if not isinstance(metrics, dict):
            raise TypeError("'metrics' must be a JSON object")
        float_metrics: dict[str, float] = {}
        for k, v in metrics.items():
            if not isinstance(v, (int, float)):
                raise TypeError(f"Metric '{k}' must be numeric, got {type(v).__name__}")
            float_metrics[k] = float(v)
        return cls(
            run_id=str(data["run_id"]),
            model=str(data["model"]),
            dataset=str(data["dataset"]),
            timestamp=str(data["timestamp"]),
            metrics=float_metrics,
            metadata={k: v for k, v in data.items() if k not in set(_required)},
        )

    @classmethod
    def from_file(cls, path: str | Path) -> "EvalRun":
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Eval run file not found: {path}")
        with p.open() as f:
            data = json.load(f)
        return cls.from_dict(data)
