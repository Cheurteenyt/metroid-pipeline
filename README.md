# Metroid Pipeline — External Execution Runner

This repository provides a **GitHub Actions runner** for the
[Metroid Prime Remastered decompilation project](https://gitlab.com/cheurteen/metroid).

## Architecture

```
GitLab (cheurteen/metroid)     ← source of truth
         │
         ▼
GitHub Actions runner          ← external execution
         │
         ▼
proof artifact (run.json)      ← evidence
```

## Roles

- **GitLab `cheurteen/metroid`**: authoritative source code, verification
  machinery, and verified manifest. Never modified by the runner.
- **GitHub `Cheurteenyt/metroid-pipeline`**: external runner only.
  Executes tests at an exact commit SHA and produces proof artifacts.
- **GPT-5.6**: analysis and pilot agent. Triggers workflows and reads
  artifacts. Cannot run local builds.
- **GLM 5.2**: execution agent. Has local LLVM/AArch64 environment.
  Bootstrap runner infrastructure and performs actual verification.

## Workflow

File: `.github/workflows/metroid-smoke.yml`

Triggered manually with:
- `source_commit`: exact 40-char SHA (required, immutable)
- `profile`: `smoke` (Python-only tests, no LLVM)

The workflow:
1. Validates the SHA is a full 40-char hash (rejects branch names)
2. Checks out the exact SHA from GitLab
3. Verifies `git rev-parse HEAD == source_commit`
4. Runs pure Python tests (no LLVM needed)
5. Produces `proof/run.json` with execution evidence
6. Uploads `proof/` as a GitHub Actions artifact

## Smoke vs EXACT

A `smoke` PASS means:
> The requested tests ran and passed at the requested commit.

A `smoke` PASS does **NOT** mean:
> The decompilation is correct or EXACT.

The `run.json` never contains `EXACT`, `verified`, `semantic`, or `coverage`
fields for a smoke test. Those concepts belong to `exact_compare.py` and
`verified_manifest.json` in the GitLab repo.

## Security

- No secrets in this repository
- No GitLab CI pipeline (intentionally disabled)
- Runner results never automatically modify GitLab
- Artifacts serve as proof of execution only

## Proof contract

See `docs/PROOF_CONTRACT.md` for the artifact schema.

## Credits

Prepared with GPT-5.6
Execution performed by GLM 5.2
