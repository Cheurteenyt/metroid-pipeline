# Tokens, Limits, and GLM 5.2 Strategy

## GitLab Fine-Grained Personal Access Tokens

### What You Need for Cloning

For the runner to clone cheurteen/metroid (read-only), you need **only one permission**:

- **Scope**: read_repository
- **Description**: Grants read access (pull) to repositories
- **Access**: Git-over-HTTP or repository files API

This is the **minimum required permission**. No other scopes are needed for cloning.

### Why You Had to Check Many Boxes

GitLab's fine-grained tokens have a complex permission system with many options:

- Code: Read, Write, Delete (for files)
- Repository: Read, Write, Delete (for repo operations)
- Issues: Read, Write
- Merge Requests: Read, Write
- Pipelines: Read, Write
- Runners: Read, Manage
- And many more...

For our use case (cloning only), you should check:
- Code: **Download** (or Read)
- Repository: **Read**

Everything else can be left unchecked.

### Alternative: Project Access Token

Instead of a personal access token, you could create a **project access token**:

1. Go to https://gitlab.com/cheurteen/metroid/-/settings/access_tokens
2. Create a token with:
   - Name: github-runner
   - Scopes: read_repository only
   - Expires: 90 days
3. Use this token in GitHub Secrets

Project access tokens are scoped to a single project and don't have access to your other projects.

## GitHub Actions Limits

### For Public Repositories (like ours)

**Unlimited minutes for standard runners:**

- Linux runners: Unlimited
- macOS runners: Unlimited
- Windows runners: Unlimited
- Storage: 10 GB per repository

This means we can run GitHub Actions as much as we want without worrying about limits.

### For Private Repositories

If the repo were private:
- GitHub Free: 2,000 minutes/month
- GitHub Pro: 3,000 minutes/month
- GitHub Team: 50,000 minutes/month

But since our runner repo is **public**, we have unlimited minutes.

## GLM 5.2 on GitHub Actions

### Current Setup

Currently, GLM 5.2 runs LLVM/AArch64 verification **locally** on your machine.

### Proposed: Move to GitHub Actions

We can create a workflow that runs LLVM verification in GitHub Actions:

1. Install LLVM 17 + AArch64 toolchain in the runner
2. Clone metroid at exact SHA
3. Build functions with cross-compilation
4. Run exact_compare.py
5. Generate proofs with EXACT/SEMANTIC/UNKNOWN status

### Advantages

1. **No local machine needed**: GLM 5.2 doesn't need LLVM installed locally
2. **Reproducible**: Every run uses the same environment
3. **Unlimited**: GitHub Actions is free for public repos
4. **Scalable**: Can run multiple exact verifications in parallel

### Limitations

1. **Binary storage**: main.elf must be accessible (private artifact or secure storage)
2. **Build time**: LLVM builds can take 5-15 minutes
3. **Complexity**: Requires setting up cross-compilation toolchain

## Next Steps

### Immediate

1. **Verify smoke-0023**: It's in failed/ but was actually PASS (7/7 tests passed)
2. **Fix workflow**: Make the status detection more robust
3. **Test again**: Create smoke-0024 to verify the fix

### Phase 2: Exact Profile

Once smoke is stable:

1. Create metroid-exact.yml workflow
2. Install LLVM 17 + AArch64 toolchain
3. Build functions and run exact_compare.py
4. Generate proofs with EXACT/SEMANTIC/UNKNOWN status
5. Test on 5-10 Rosetta Stones

### Phase 3: Regression Profile

After exact is working:

1. Create metroid-regression.yml workflow
2. Compare baseline vs candidate commits
3. Use regression_gate.py to detect regressions
4. Prevent loss of verified functions

## Recommendations

### For GitLab Token

- Keep the current token (it works)
- Next rotation: use only read_repository scope
- Or use a project access token instead

### For GitHub Actions

- We have unlimited minutes (public repo)
- No need to worry about limits
- Can scale to run many exact verifications

### For GLM 5.2

- Move LLVM verification to GitHub Actions
- No need for local machine
- More reproducible and scalable

## Summary

| Component | Current | Recommended |
|-----------|---------|-------------|
| GitLab Token | Many permissions | read_repository only |
| GitHub Actions | Smoke tests | Add exact + regression |
| GLM 5.2 | Local LLVM | GitHub Actions |
| Limits | GitLab 400min | GitHub unlimited |
| Security | Token in secret | Rotate regularly |

The infrastructure is ready for Phase 2 (exact verification).