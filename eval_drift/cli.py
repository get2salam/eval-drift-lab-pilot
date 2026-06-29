#!/usr/bin/env python3
"""eval-drift CLI: compare model-evaluation JSON runs and flag metric drift."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from eval_drift.drift import compare
from eval_drift.parser import EvalRun


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="eval-drift",
        description="Compare model-evaluation JSON runs and flag metric drift.",
    )
    sub = p.add_subparsers(dest="command", required=True)

    cmp = sub.add_parser(
        "compare",
        help="Compare a baseline run against a candidate run.",
    )
    cmp.add_argument("baseline", help="Path to baseline JSON eval run")
    cmp.add_argument("candidate", help="Path to candidate JSON eval run")
    cmp.add_argument(
        "--threshold",
        "-t",
        type=float,
        default=0.05,
        help="Absolute drift threshold per metric (default: 0.05)",
    )
    cmp.add_argument(
        "--metrics",
        "-m",
        nargs="+",
        help="Limit comparison to specific metrics",
    )
    cmp.add_argument(
        "--json",
        "-j",
        action="store_true",
        dest="json_output",
        help="Output raw JSON instead of the human-readable report",
    )
    return p


def _cmd_compare(args: argparse.Namespace) -> int:
    baseline = EvalRun.from_file(args.baseline)
    candidate = EvalRun.from_file(args.candidate)
    report = compare(baseline, candidate, threshold=args.threshold, metrics=args.metrics)

    if args.json_output:
        data = {
            "baseline_id": report.baseline_id,
            "candidate_id": report.candidate_id,
            "threshold": report.threshold,
            "has_drift": report.has_drift,
            "results": [
                {
                    "metric": r.name,
                    "baseline": r.baseline,
                    "candidate": r.candidate,
                    "delta": r.delta,
                    "drifted": r.drifted,
                }
                for r in report.results
            ],
        }
        print(json.dumps(data, indent=2))
    else:
        print(report.summary())

    return 1 if report.has_drift else 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "compare":
        return _cmd_compare(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
