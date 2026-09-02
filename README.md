# Metroid Pipeline - External Execution Runner

**GitHub Actions runner for the Metroid Prime Remastered decompilation project.**

This repository is **strictly an execution runner only**. It contains no source code, no datasets, and no binaries from the main project.

## Architecture

GitLab (cheurteen/metroid) -> GitHub Actions runner -> Proof artifacts

- GitLab: Source of truth (code, tests, manifest). NEVER modified by this runner.
- GitHub: External runner only. Contains NO source code from GitLab.
- Artifacts: Immutable proof (run.json, test-results.json, logs).

## Repository Contents

- `.github/workflows/metroid-smoke.yml` - Smoke test workflow
- `scripts/` - Runner scripts (parse, generate, check)
- `requests/pending/` - New test requests
- `requests/completed/` - Successfully processed requests
- `requests/failed/` - Failed requests
- `docs/` - Documentation

**What this repo does NOT contain:**
- No source code from GitLab
- No datasets or binaries
- No verified manifest

## How It Works

1. Create request JSON in `requests/pending/`
2. Push to GitHub (triggers workflow)
3. Workflow clones GitLab at exact SHA using secret
4. Runs 7 smoke tests (pure Python)
5. Generates proof artifacts
6. Moves request to `completed/` or `failed/`

## Security

### Secrets
- `GITLAB_TOKEN` - Read-only access to GitLab (stored encrypted in GitHub Secrets)
- No secrets in code or committed to repo

### Token Rotation
**GitLab token:**
1. Prefer a fine-grained personal access token scoped to project `cheurteen/metroid`
2. Grant only `Code -> Download` (needed for git clone/fetch); do not grant Code Push
3. If using a legacy token, use the comparable minimal scope `read_repository`
4. Update `GITLAB_TOKEN` secret in GitHub -> Settings -> Secrets

**GitHub PAT:**
1. Revoke old token in GitHub -> Settings -> Developer settings -> Personal access tokens
2. Create new fine-grained token with Contents read/write, Metadata read, Actions read

After rotation: Runner continues with new token. No code changes required.

## Profiles

### Phase 1: Smoke (current)
- 7 pure Python tests (no LLVM)
- Result: PASS if all tests pass
- Does NOT mean decompilation is EXACT

### Phase 2: Exact (future)
- Opcode-exact verification with LLVM 17
- Requires main.elf (stored securely, not in this repo)

### Phase 3: Regression (future)
- Detect regressions between commits

## Model Roles

| Model | Role | Commits |
|-------|------|---------|
| GPT-5.6 | Analysis and pilot | [GPT-5.6] |
| GLM 5.2 | Execution with LLVM | [GLM-5.2] |
| Qwen 3.8 Max | Documentation, audit | [qwen3.8-max] |

## Dependencies
- Python 3.12, setuptools==69.0.3, capstone==5.0.1, pytest==8.3.2
- All versions pinned and recorded in run.json

## Credits
- GPT-5.6: Initial architecture
- GLM 5.2: Execution infrastructure
- Qwen 3.8 Max: Documentation and coordination

## Links
- Source: https://gitlab.com/cheurteen/metroid
- Runner: https://github.com/Cheurteenyt/metroid-pipeline