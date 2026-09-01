# Smoke Test Requests

## How to request a smoke test

Create a file in `requests/pending/`:

```
requests/pending/<request-id>.json
```

## Request format

```json
{
  "request_id": "smoke-0001",
  "source_repo": "gitlab.com/cheurteen/metroid",
  "source_commit": "7d58c21bb96a3dbaae3d59ff02e4f62e26dcd0bf",
  "profile": "smoke"
}
```

## Rules

- `request_id`: non-empty string, unique per request
- `source_repo`: must be exactly `gitlab.com/cheurteen/metroid`
- `source_commit`: must be exactly 40 hex characters
- `profile`: must be `smoke` for this POC

Any other value causes the workflow to FAIL.

## Triggering

Pushing a new or modified `requests/pending/*.json` file triggers the
GitHub Actions workflow automatically.

The workflow:
1. Detects which request files were added/modified in the push
2. Validates the request
3. Checks out the exact SHA from GitLab
4. Runs the 7 smoke tests
5. Produces a proof artifact

## Multiple requests

For this POC, pushing more than one request in a single commit causes FAIL.
Use separate commits for separate requests.

## Anti-replay

The runner does NOT delete requests automatically. If the same request file
is pushed again (e.g. via a force-push), the workflow will run again. This
is acceptable for the POC — production anti-replay will be added later.

## PASS != EXACT

A `PASS` status means the smoke tests ran successfully. It does NOT mean:
- The decompilation is correct
- Any function is EXACT
- Coverage increased

See `docs/PROOF_CONTRACT.md` for details.
