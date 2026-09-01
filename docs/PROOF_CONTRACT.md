# Proof Contract

## Artifact: `proof/`

Every workflow run produces a `proof/` directory containing:

### `run.json`

```json
{
  "runner_repo": "Cheurteenyt/metroid-pipeline",
  "runner_commit": "<sha>",
  "source_repo": "gitlab.com/cheurteen/metroid",
  "requested_source_commit": "<sha>",
  "checked_out_source_commit": "<sha>",
  "source_sha_match": true,
  "profile": "smoke",
  "runner_os": "Linux 6.x ...",
  "python_version": "Python 3.12.x",
  "timestamp_utc": "2026-...",
  "status": "PASS|FAIL",
  "tests_expected": 7,
  "tests_found": 7,
  "tests_executed": 7,
  "tests_passed": 7,
  "tests_failed": 0,
  "tests_missing": 0,
  "commands": [...]
}
```

### `test-results.json`

Array of `{test, status}` objects for EVERY expected test:

```json
[
  {"test": "switch/scripts/test_experiment_record.py", "status": "PASS"},
  {"test": "switch/scripts/test_candidate_schema.py", "status": "PASS"},
  ...
]
```

A missing test file produces `{"status": "MISSING"}` — never silently skipped.

### `stdout.txt` / `stderr.txt`

Captured output from all test runs.

## Status semantics

| Status | Meaning |
|--------|---------|
| `PASS` | All expected tests found, executed, and passed. SHA verified. |
| `FAIL` | Any test missing, failed, or SHA mismatch. |

### `PASS` does NOT mean:
- The decompilation is correct
- Any function is `EXACT`
- Coverage increased
- The verified manifest changed

### `PASS` requires ALL of:
- `tests_missing == 0`
- `tests_failed == 0`
- `tests_executed == tests_expected`
- `tests_expected > 0`
- `source_sha_match == true`

## SHA verification

The workflow refuses to run if:
- `source_commit` is not a 40-character hex string
- `source_commit` is a branch name (`main`, `HEAD`, etc.)
- The checkout SHA does not match the requested SHA

## Anti-false-PASS rules

1. A missing test is `MISSING`, never `SKIP`
2. `tests_executed != tests_expected` → `FAIL`
3. `tests_expected == 0` → `FAIL`
4. SHA mismatch → `FAIL`
5. `status` is computed from metrics, never hardcoded
6. `run.json` never contains `EXACT`, `verified`, `semantic`, or `coverage` for smoke

## Invariants

```
tests_found + tests_missing = tests_expected
tests_passed + tests_failed = tests_executed
tests_executed == tests_expected  (required for PASS)
```
