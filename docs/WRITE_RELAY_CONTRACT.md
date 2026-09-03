# Write Relay Contract

## Overview

The write relay allows authorized AI models to request controlled mutations
to the `Cheurteenyt/metroid-pipeline` GitHub repository via a declarative,
validated, fail-closed protocol.

## Architecture

```
GPT-5.6 / qwen3.8-max / GLM 5.2
    |
    | push requests/write/<id>.json to GitHub
    |
    v
GitHub Actions (metroid-write-relay.yml)
    |
    | validate request (schema, paths, model, SHA)
    | verify base_sha matches HEAD
    | create automation/<model>/<id> branch
    | apply patches
    | run tests
    | if tests pass: commit + push
    | produce proof artifact
    |
    v
proof/github-write/<id>/run.json
```

## Request format

File: `requests/write/<request-id>.json`

```json
{
  "schema": "github-write-request/v1",
  "request_id": "write-001",
  "target_repo": "Cheurteenyt/metroid-pipeline",
  "target_branch": "ignored — branch is auto-generated",
  "base_sha": "<40-char hex SHA of current HEAD>",
  "author_model": "GPT 5.6",
  "operation": "patch",
  "files": [
    {"path": "docs/example.md", "patch": "# content"}
  ],
  "commit_message": "[GPT-5.6] add example doc",
  "required_checks": ["python-tests"]
}
```

## Validation rules

1. **Schema**: must be exactly `github-write-request/v1`
2. **request_id**: non-empty, alphanumeric + `_-` only
3. **target_repo**: must be `Cheurteenyt/metroid-pipeline`
4. **author_model**: must be `GPT 5.6`, `qwen3.8-max`, or `GLM 5.2`
5. **base_sha**: 40 hex chars, must match current HEAD
6. **target_branch**: auto-generated as `automation/<model>/<request-id>`
7. **files**: max 10 files, max 10KB per file, max 50KB total
8. **Deny paths**: `.github/workflows/**`, `.git/**`, `secrets/**`, `.env*`, `*.pem`, `*.key`, path traversal, absolute paths
9. **commit_message**: must start with model prefix `[GPT-5.6]` / `[qwen3.8-max]` / `[GLM-5.2]`

## Fail-closed rules

- Tests FAIL → no push
- Validation FAIL → no push
- SHA mismatch → no push
- Any error → no push
- `status: PASS` requires: validation OK + tests pass + push confirmed

## Proof artifact

`proof/github-write/<request-id>/run.json`:

```json
{
  "schema": "github-write-proof/v1",
  "request_id": "write-001",
  "status": "PASS|FAIL|UNKNOWN",
  "base_sha": "...",
  "result_sha": "...",
  "branch": "automation/gpt-5.6/write-001",
  "files_changed": ["docs/example.md"],
  "tests": {"expected": 5, "executed": 5, "passed": 5, "failed": 0},
  "push_confirmed": true
}
```

## Anti-replay

- GitHub Actions `concurrency` prevents parallel runs
- Each request_id generates a unique branch name
- A request can be replayed (same request_id) but will create a new branch
  with the same name (overwriting if the branch was deleted)

## What PASS means

`PASS` means: the requested patch was applied, tests passed, and the
commit was pushed to the automation branch.

`PASS` does NOT mean:
- The patch is correct
- The patch should be merged to main
- Any decompilation claim is verified
