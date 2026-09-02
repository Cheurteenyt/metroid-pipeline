# Setup Guide - Create `GITLAB_TOKEN`

The GitHub workflow clones `gitlab.com/cheurteen/metroid` over HTTPS with the encrypted repository secret `GITLAB_TOKEN`.

## Recommended GitLab token

Use a **fine-grained personal access token** scoped only to project `cheurteen/metroid`.

Minimum permission for this runner:

| Operation | Resource | Permission | Access boundary |
|---|---|---|---|
| `git clone` / `git fetch` / Git LFS download | Code | Download | Project `cheurteen/metroid` |

Do **not** grant Code Push. The runner never writes to GitLab.

If you use a legacy/coarse token instead of a fine-grained token, the comparable minimal scope is `read_repository`.

## Create or adjust the GitLab token

1. Open GitLab token settings.
2. Create a fine-grained personal access token for project `cheurteen/metroid`.
3. Grant only: **Code -> Download**.
4. Set an expiration date and copy the token.

If the UI does not show `Code -> Download`, use a legacy/project token with `read_repository`, or use the GitLab permissions assistant to locate the Git operation permission.

## Add it to GitHub

1. Go to `https://github.com/Cheurteenyt/metroid-pipeline/settings/secrets/actions`.
2. Create or update repository secret named exactly `GITLAB_TOKEN`.
3. Paste the GitLab token value.

## Test

Add a request in `requests/pending/*.json` and push. Expected result:

- GitHub Actions run succeeds.
- Artifact `proof-<request-id>` contains `run.json` with `status: PASS`.
- Request is moved automatically to `requests/completed/` by `GITHUB_TOKEN`.

## GitHub token usage

No personal GitHub PAT is required for normal operation. The workflow uses GitHub's built-in `GITHUB_TOKEN` with `contents: write` to move request files.

A personal GitHub PAT is only needed if an external operator modifies files in this runner repository through the API.

## Rotation

After the new secret works:

1. Revoke any old GitLab token that was exposed.
2. Revoke any temporary GitHub PAT used for setup, unless you still need API write access.
3. For future rotation, create a new GitLab token with the same `Code -> Download` permission and update the GitHub secret. No code change is required.
