# Proof Contract

## Artifact: `proof/<request-id>/`

Every workflow run produces a `proof/<request-id>/` directory containing:

### `run.json`

```json
{
  "request_id": "smoke-0001",
  "runner_repo": "Cheurteenyt/metroid-pipeline",
  "runner_commit": "<sha>",
  "trigger_commit": "<github-push-sha>",
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

Array of `{test, status}` for EVERY expected test:

```json
[
  {"test": "switch/scripts/test_experiment_record.py", "status": "PASS"},
  {"test": "switch/scripts/test_candidate_schema.py", "status": "PASS"},
  ...
]
```

Missing test → `{"status": "MISSING"}`. Never silently skipped.

### `stdout.txt` / `stderr.txt`

Captured output from all test runs.

## Status semantics

| Status | Meaning |
|--------|---------|
| `PASS` | All expected tests found, executed, and passed. SHA verified. |
| `FAIL` | Any test missing, failed, SHA mismatch, or validation error. |

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
6. `run.json` never contains `EXACT`, `verified`, `semantic`, or `coverage`
7. Multiple requests in one push → `FAIL`

## Invariants

```
tests_found + tests_missing = tests_expected
tests_passed + tests_failed = tests_executed
tests_executed == tests_expected  (required for PASS)
```

## Anti-replay (POC limitation)

The runner does NOT delete request files. If the same request is pushed
again, the workflow runs again. This is acceptable for the POC.
Production anti-replay will track executed request_ids.
