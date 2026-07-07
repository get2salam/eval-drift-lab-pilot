# Eval Drift Lab

[![Tests](https://github.com/get2salam/eval-drift-lab-pilot/actions/workflows/test.yml/badge.svg)](https://github.com/get2salam/eval-drift-lab-pilot/actions/workflows/test.yml)

A CLI toolkit that compares model-evaluation JSON runs and flags metric drift. Point it at two evaluation snapshots and it tells you which metrics regressed, by how much, and exits non-zero if anything exceeds your threshold — making it drop-in ready for CI pipelines.

---

## Problem

Model evaluations don't break loudly. Accuracy quietly slips from 0.82 to 0.75 after a fine-tune, precision tanks after a data pipeline change, or latency doubles across a release — and no test turns red. Eval Drift Lab gives you a structured, scriptable way to diff evaluation runs and fail fast when metrics drift beyond an acceptable band.

---

## Features

- **JSON eval-run parser** — validates and loads structured evaluation snapshots with required fields (`run_id`, `model`, `dataset`, `timestamp`, `metrics`)
- **Drift comparison engine** — computes per-metric deltas, flags anything exceeding an absolute threshold (default `±0.05`)
- **Human-readable table output** — quick visual diff with DRIFT / OK labels per metric
- **Machine-readable JSON output** (`--json`) — pipe results into downstream scripts or dashboards
- **Metric filter** (`--metrics`) — compare a subset of metrics for targeted checks
- **CI-friendly exit codes** — exits `1` on drift, `0` when clean; integrates with any CI system
- **Zero dependencies** — pure Python stdlib, no install beyond `pip install -e .`

---

## Project structure

```
eval-drift-lab-pilot/
├── eval_drift/
│   ├── __init__.py       # package version
│   ├── __main__.py       # python -m eval_drift entry point
│   ├── parser.py         # EvalRun dataclass + JSON loader/validator
│   ├── drift.py          # compare() engine + DriftReport
│   └── cli.py            # argparse CLI (eval-drift compare ...)
├── examples/
│   └── detect_renamed_metrics.py  # runnable example: catch metrics that vanish on rename
├── tests/
│   ├── fixtures/
│   │   ├── baseline.json                 # reference evaluation run
│   │   ├── candidate_ok.json              # no drift (all deltas < 0.05)
│   │   ├── candidate_drifted.json         # drift detected (accuracy, precision)
│   │   └── candidate_renamed_metric.json  # "recall" renamed to "recall_score"
│   ├── test_parser.py    # unit tests for the parser
│   ├── test_drift.py     # unit tests for the comparison engine
│   ├── test_cli.py       # integration tests for the CLI
│   └── test_examples.py  # guard test for examples/detect_renamed_metrics.py
├── .github/workflows/test.yml
├── pyproject.toml
└── README.md
```

---

## Quickstart

**No install (run as module):**

```bash
python -m eval_drift compare tests/fixtures/baseline.json tests/fixtures/candidate_drifted.json
```

**Or install the `eval-drift` command:**

```bash
pip install -e .
eval-drift compare tests/fixtures/baseline.json tests/fixtures/candidate_drifted.json
```

---

## Example input

**`tests/fixtures/baseline.json`**
```json
{
  "run_id": "run-2024-06-01",
  "model": "gpt-4o-mini",
  "dataset": "qa-benchmark-v1",
  "timestamp": "2024-06-01T10:00:00Z",
  "metrics": {
    "accuracy": 0.823,
    "f1": 0.801,
    "precision": 0.815,
    "recall": 0.788
  }
}
```

**`tests/fixtures/candidate_drifted.json`**
```json
{
  "run_id": "run-2024-06-15",
  "model": "gpt-4o-mini",
  "dataset": "qa-benchmark-v1",
  "timestamp": "2024-06-15T10:00:00Z",
  "metrics": {
    "accuracy": 0.756,
    "f1": 0.796,
    "precision": 0.742,
    "recall": 0.794
  }
}
```

---

## Example output

**Drift detected (exit code 1):**

```
$ python -m eval_drift compare tests/fixtures/baseline.json tests/fixtures/candidate_drifted.json

Eval Drift Report
=================
Baseline : run-2024-06-01  (gpt-4o-mini / qa-benchmark-v1)
Candidate: run-2024-06-15  (gpt-4o-mini / qa-benchmark-v1)

Metric         Baseline   Candidate       Delta  Status
-------------------------------------------------------
accuracy         0.8230      0.7560     -0.0670  DRIFT
f1               0.8010      0.7960     -0.0050  OK
precision        0.8150      0.7420     -0.0730  DRIFT
recall           0.7880      0.7940     +0.0060  OK

Drifted metrics: 2 / 4  (threshold: ±0.05)
Status: DRIFT DETECTED (exit code 1)
```

**No drift (exit code 0):**

```
$ python -m eval_drift compare tests/fixtures/baseline.json tests/fixtures/candidate_ok.json

Eval Drift Report
=================
Baseline : run-2024-06-01  (gpt-4o-mini / qa-benchmark-v1)
Candidate: run-2024-06-08  (gpt-4o-mini / qa-benchmark-v1)

Metric         Baseline   Candidate       Delta  Status
-------------------------------------------------------
accuracy         0.8230      0.8270     +0.0040  OK
f1               0.8010      0.7980     -0.0030  OK
precision        0.8150      0.8190     +0.0040  OK
recall           0.7880      0.7910     +0.0030  OK

Drifted metrics: 0 / 4  (threshold: ±0.05)
Status: CLEAN (exit code 0)
```

**JSON output (pipe-friendly):**

```
$ python -m eval_drift compare tests/fixtures/baseline.json tests/fixtures/candidate_drifted.json --json

{
  "baseline_id": "run-2024-06-01",
  "candidate_id": "run-2024-06-15",
  "threshold": 0.05,
  "has_drift": true,
  "results": [
    { "metric": "accuracy",  "baseline": 0.823, "candidate": 0.756, "delta": -0.067, "drifted": true },
    { "metric": "f1",        "baseline": 0.801, "candidate": 0.796, "delta": -0.005, "drifted": false },
    { "metric": "precision", "baseline": 0.815, "candidate": 0.742, "delta": -0.073, "drifted": true },
    { "metric": "recall",    "baseline": 0.788, "candidate": 0.794, "delta":  0.006, "drifted": false }
  ]
}
```

---

## CLI reference

```
eval-drift compare <baseline> <candidate> [options]

Arguments:
  baseline              Path to baseline JSON eval run
  candidate             Path to candidate JSON eval run

Options:
  -t, --threshold FLOAT Absolute drift threshold per metric (default: 0.05)
  -m, --metrics M [M…]  Limit comparison to specific metrics
  -j, --json            Output raw JSON instead of human-readable report
```

**CI integration example:**

```yaml
- name: Check for eval drift
  run: |
    python -m eval_drift compare eval_runs/baseline.json eval_runs/latest.json \
      --threshold 0.03 --metrics accuracy f1
```

---

## Gotcha: renamed metrics vanish silently

`compare()` only scores metric names present in **both** runs — it skips any
key that's missing from either side rather than flagging it. So if a pipeline
change renames a metric between eval runs (`recall` becomes `recall_score`),
neither name appears in the report. There's no DRIFT flag and no warning —
the metric just isn't there, which can read as "nothing to see here" instead
of "this metric disappeared."

`examples/detect_renamed_metrics.py` reproduces this against the bundled
fixtures and shows the two-line guard you can add to your own CI script to
catch it — compare the metric *key sets* yourself before trusting the report:

```bash
python examples/detect_renamed_metrics.py
```

```
Eval Drift Report
=================
Baseline : run-2024-06-01  (gpt-4o-mini / qa-benchmark-v1)
Candidate: run-2024-06-22  (gpt-4o-mini / qa-benchmark-v1)

Metric         Baseline   Candidate       Delta  Status
-------------------------------------------------------
accuracy         0.8230      0.8270     +0.0040  OK
f1               0.8010      0.7980     -0.0030  OK
precision        0.8150      0.8190     +0.0040  OK

Drifted metrics: 0 / 3  (threshold: ±0.05)
Status: CLEAN (exit code 0)

Guard: 2 metric(s) present in only one run and silently excluded from the report above: ['recall', 'recall_score']
```

`eval-drift` itself reports `CLEAN`, but the guard (exit code 1) shows that
`recall` quietly disappeared. Treat "no drift" as "no drift among the metrics
that survived the comparison," not "nothing changed."

---

## Verification

```bash
python -m unittest discover -s tests -v
```

Expected output: `Ran 54 tests in <time>s — OK`

---

## License

MIT
