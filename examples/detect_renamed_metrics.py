#!/usr/bin/env python3
"""Runnable example: catch metrics that silently vanish from a drift report.

``compare()`` only scores metric names present in *both* runs (see the
``continue`` in ``eval_drift/drift.py``). If a metric gets renamed between eval
runs — a pipeline change starts emitting ``recall_score`` instead of
``recall`` — neither the old nor the new name shows up in the report. There is
no DRIFT flag and no warning; the metric is simply absent, which reads as
"nothing to see here" instead of "this metric disappeared."

This script reproduces the pitfall against the bundled fixtures and shows the
two-line guard you can drop into your own CI script to catch it.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from eval_drift.drift import compare
from eval_drift.parser import EvalRun

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures"


def find_orphaned_metrics(baseline: EvalRun, candidate: EvalRun) -> set[str]:
    """Metric names present in only one run — ``compare()`` silently drops these."""
    return set(baseline.metrics) ^ set(candidate.metrics)


def main() -> int:
    baseline = EvalRun.from_file(FIXTURE_DIR / "baseline.json")
    candidate = EvalRun.from_file(FIXTURE_DIR / "candidate_renamed_metric.json")

    report = compare(baseline, candidate)
    print(report.summary())
    print()

    orphaned = find_orphaned_metrics(baseline, candidate)
    if orphaned:
        print(
            f"Guard: {len(orphaned)} metric(s) present in only one run and "
            f"silently excluded from the report above: {sorted(orphaned)}"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
