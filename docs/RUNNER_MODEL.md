# Runner Model

## Topology

```
GPT-5.6 (GitLab UI)
    │
    │  "Test commit X with profile Y"
    │
    ▼
GitHub Actions (metroid-pipeline)
    │
    │  checkout exact SHA from GitLab
    │  run tests
    │  collect output
    │
    ▼
proof/ artifact
    │
    ▼
GPT-5.6 reads artifact
```

## Phase 1: Smoke (current)

- Profile: `smoke`
- Tests: pure Python tests (`test_experiment_record.py`, etc.)
- No LLVM, no compilation, no verification
- Purpose: validate the execution channel

## Phase 2: Exact verification (future)

- Profile: `exact`
- Tests: `exact_compare.py`, `full_audit.py`
- Requires: LLVM 17, capstone, main.elf
- Purpose: verify EXACT status at a specific commit

## Phase 3: Regression (future)

- Profile: `regression`
- Tests: `regression_gate.py` with baseline + candidate manifests
- Purpose: detect regressions between commits

## Rules

1. GitLab is the source of truth
2. GitHub is the runner only
3. SHA must be immutable (40-char hex)
4. Smoke PASS ≠ EXACT
5. No GitLab CI pipeline
6. No secrets in the runner repo
7. Artifacts are the only proof
