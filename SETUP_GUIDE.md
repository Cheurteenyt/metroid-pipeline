# Setup Guide - Create GITLAB_TOKEN Secret

## Why This Is Needed

The workflow now uses `${{ secrets.GITLAB_TOKEN }}` to clone the GitLab repository. This token must be created manually in GitHub.

## Step-by-Step Instructions

### Step 1: Create a New GitLab PAT

1. Go to https://gitlab.com/-/profile/personal_access_tokens
2. Token name: `github-runner-access`
3. Expiration date: 90 days from now
4. Select scopes: Check only `read_repository`
5. Click Create personal access token
6. Copy the token (starts with `glpat-`)

### Step 2: Add the Token to GitHub Secrets

1. Go to https://github.com/Cheurteenyt/metroid-pipeline/settings/secrets/actions
2. Click New repository secret
3. Name: `GITLAB_TOKEN` (exact name, all caps)
4. Value: Paste the GitLab PAT from Step 1
5. Click Add secret

### Step 3: Test the Setup

The workflow should have already been triggered by smoke-0023.json.

Check the workflow run:
1. Go to https://github.com/Cheurteenyt/metroid-pipeline/actions
2. Wait for the workflow to complete
3. Expected result: PASS (7/7 tests)

### Step 4: Revoke Old Tokens (Security)

After confirming the new setup works:

1. Revoke the old GitLab PAT that was exposed in the workflow
2. Optionally revoke the GitHub fine-grained PAT you shared

## Troubleshooting

**Workflow fails with authentication error:**
- Check that GITLAB_TOKEN secret exists
- Verify the token has read_repository scope
- Ensure the token hasn't expired

**Request stays in pending/:**
- Check workflow logs for errors
- The request should be moved automatically on success

## What Happens After Setup

- Normal operation: No further action needed
- Creating requests: Add JSON to requests/pending/ and push
- Checking results: View artifacts or check requests/completed/
- Token rotation: Update the secret when the token expires

## Security Best Practices

- Never commit tokens to code
- Use minimal scopes (read_repository only)
- Set expiration dates (90 days recommended)
- Rotate tokens regularly
- Revoke immediately if exposed