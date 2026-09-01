# Proof Contract

## Artifact: `proof/`

Every workflow run produces a `proof/` directory containing:

### `run.json`

```json
{
  "runner_repo": "Cheurteenyt/metroid-pipeline",
  "runner_commit": "<sha>",
  "source_repo": "gitlab.com/cheurteen/metroid",
  "source_commit": "<sha>",
  "profile": "smoke",
  "runner_os": "Linux 6.x ...",
  "python_version": "Python 3.12.x",
  "timestamp_utc": "2026-...",
  "status": "PASS|FAIL",
  "tests_passed": 5,
  "tests_failed": 0,
  "commands": [...]
}
```

### `stdout.txt`

Captured stdout from all test runs.

### `stderr.txt`

Captured stderr from all test runs.

### `test-results.json`

Array of `{test, status}` objects.

## Status semantics

| Status | Meaning |
|--------|---------|
| `PASS` | All requested tests executed and passed at the exact SHA |
| `FAIL` | One or more tests failed, or SHA checkout failed |

**`PASS` does NOT mean:**
- The decompilation is correct
- Any function is `EXACT`
- Coverage increased
- The verified manifest changed

## SHA verification

The workflow refuses to run if:
- `source_commit` is not a 40-character hex string
- `source_commit` is a branch name (`main`, `HEAD`, etc.)
- The checkout SHA does not match the requested SHA

This ensures every proof artifact is tied to an immutable source state.
