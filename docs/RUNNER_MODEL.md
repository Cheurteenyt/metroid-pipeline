# Runner Model

## Topology

```
GPT-5.6 (GitLab UI / GitHub UI)
    │
    │  Push request file to GitHub
    │  requests/pending/smoke-NNNN.json
    │
    ▼
GitHub Actions (metroid-pipeline)
    │
    │  Detect request files in push
    │  Validate request
    │  Checkout exact SHA from GitLab
    │  Run smoke tests
    │  Collect output
    │
    ▼
proof/<request-id>/ artifact
    │
    ▼
GPT-5.6 reads artifact from GitHub Actions
```

## Roles

| Entity | Role |
|--------|------|
| GitLab `cheurteen/metroid` | Source of truth (code, tests, manifest) |
| GitHub `Cheurteenyt/metroid-pipeline` | External runner only |
| GPT-5.6 | Analysis, audit, request creation |
| GLM 5.2 | Infrastructure, execution, verification |

## Phase 1: Smoke (current)

- Trigger: push to `requests/pending/*.json`
- Profile: `smoke`
- Tests: 7 pure Python tests (no LLVM)
- Purpose: validate the execution channel

## Phase 2: Exact verification (future)

- Profile: `exact`
- Tests: `exact_compare.py`, `full_audit.py`
- Requires: LLVM 17, capstone, main.elf
- Purpose: verify EXACT status at a specific commit

## Phase 3: Regression (future)

- Profile: `regression`
- Tests: `regression_gate.py`
- Purpose: detect regressions between commits

## Rules

1. GitLab is the source of truth
2. GitHub is the runner only
3. SHA must be immutable (40-char hex)
4. Smoke PASS ≠ EXACT
5. No GitLab CI pipeline
6. No secrets in the runner repo
7. Artifacts are the only proof
8. The runner never modifies GitLab
9. Multiple requests in one push → FAIL (POC limitation)

## Request lifecycle

```
GPT-5.6 creates requests/pending/smoke-0001.json
    ↓
Push to GitHub
    ↓
GitHub Actions triggers on push
    ↓
Workflow detects changed request files
    ↓
Validates request (request_id, source_repo, source_commit, profile)
    ↓
Checkout exact SHA from GitLab
    ↓
Run 7 smoke tests
    ↓
Produce proof/smoke-0001/run.json + test-results.json
    ↓
Upload as GitHub Actions artifact
    ↓
GPT-5.6 reads artifact and verifies
```

The request file is NOT deleted by the runner. Anti-replay is documented
but not enforced in this POC.

## Credits

Prepared with GPT-5.6
Execution performed by GLM 5.2
