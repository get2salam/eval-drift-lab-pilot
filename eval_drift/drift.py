"""Compare two EvalRun objects and produce a DriftReport."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from eval_drift.parser import EvalRun


@dataclass
class MetricResult:
    name: str
    baseline: float
    candidate: float
    delta: float
    drifted: bool
    threshold: float


@dataclass
class DriftReport:
    baseline_id: str
    candidate_id: str
    baseline_model: str
    candidate_model: str
    baseline_dataset: str
    candidate_dataset: str
    threshold: float
    results: list[MetricResult] = field(default_factory=list)

    @property
    def drifted_metrics(self) -> list[MetricResult]:
        return [r for r in self.results if r.drifted]

    @property
    def has_drift(self) -> bool:
        return bool(self.drifted_metrics)

    def summary(self) -> str:
        lines = [
            "Eval Drift Report",
            "=================",
            f"Baseline : {self.baseline_id}  ({self.baseline_model} / {self.baseline_dataset})",
            f"Candidate: {self.candidate_id}  ({self.candidate_model} / {self.candidate_dataset})",
        ]
        if self.baseline_model != self.candidate_model:
            lines.append(
                f"NOTE: models differ — baseline='{self.baseline_model}',"
                f" candidate='{self.candidate_model}'"
            )
        if self.baseline_dataset != self.candidate_dataset:
            lines.append(
                f"NOTE: datasets differ — baseline='{self.baseline_dataset}',"
                f" candidate='{self.candidate_dataset}'"
            )
        lines.append("")
        col_w = max((len(r.name) for r in self.results), default=10) + 2
        header = (
            f"{'Metric':<{col_w}}  {'Baseline':>10}  {'Candidate':>10}  {'Delta':>10}  Status"
        )
        lines += [header, "-" * len(header)]
        for r in self.results:
            status = "DRIFT" if r.drifted else "OK"
            lines.append(
                f"{r.name:<{col_w}}  {r.baseline:>10.4f}  {r.candidate:>10.4f}"
                f"  {r.delta:>+10.4f}  {status}"
            )
        lines += [
            "",
            f"Drifted metrics: {len(self.drifted_metrics)} / {len(self.results)}"
            f"  (threshold: ±{self.threshold})",
        ]
        if self.has_drift:
            lines.append("Status: DRIFT DETECTED (exit code 1)")
        else:
            lines.append("Status: CLEAN (exit code 0)")
        return "\n".join(lines)


def compare(
    baseline: EvalRun,
    candidate: EvalRun,
    threshold: float = 0.05,
    metrics: Optional[list[str]] = None,
) -> DriftReport:
    """Compare baseline and candidate eval runs; flag metrics exceeding *threshold*."""
    all_keys = metrics or sorted(set(baseline.metrics) | set(candidate.metrics))
    results: list[MetricResult] = []
    for key in all_keys:
        if key not in baseline.metrics or key not in candidate.metrics:
            continue
        b = baseline.metrics[key]
        c = candidate.metrics[key]
        delta = c - b
        results.append(
            MetricResult(
                name=key,
                baseline=b,
                candidate=c,
                delta=delta,
                drifted=abs(delta) > threshold,
                threshold=threshold,
            )
        )
    return DriftReport(
        baseline_id=baseline.run_id,
        candidate_id=candidate.run_id,
        baseline_model=baseline.model,
        candidate_model=candidate.model,
        baseline_dataset=baseline.dataset,
        candidate_dataset=candidate.dataset,
        threshold=threshold,
        results=results,
    )
