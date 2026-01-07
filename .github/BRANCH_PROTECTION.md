# Branch Protection Setup

This document describes how to set up branch protection rules for the `main` branch to enforce CI checks and prevent direct commits.

## Required Steps

### 1. Enable Branch Protection

Go to: **Repository Settings → Branches → Add branch protection rule**

### 2. Configure Protection Rules

**Branch name pattern:** `main`

**Required Settings:**

- ✅ **Require a pull request before merging**
  - ✅ Require approvals: 1 (adjust based on team size)
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from Code Owners (optional, if using CODEOWNERS)

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - **Required status checks:**
    - `Lint`
    - `Test (Python 3.11)`
    - `Test (Python 3.12)`
    - `All checks passed`

- ✅ **Require conversation resolution before merging** (recommended)

- ✅ **Require linear history** (optional, enforces rebase/squash)

- ✅ **Do not allow bypassing the above settings** (recommended)

- ✅ **Restrict who can push to matching branches**
  - Only allow administrators (prevents direct commits to main)

### 3. Additional Recommended Settings

- ✅ **Allow force pushes:** Disabled
- ✅ **Allow deletions:** Disabled

## Enforcement

Once enabled, all changes to `main` must:

1. Be submitted via pull request
2. Pass all CI checks (lint + tests)
3. Be reviewed and approved by at least 1 person
4. Have all conversations resolved

Direct commits to `main` will be blocked, even for administrators.

## Emergency Override

Repository administrators can temporarily disable branch protection in extreme emergencies, but this should be:

1. Documented in an incident report
2. Re-enabled immediately after the emergency
3. Followed up with a post-mortem

## Verification

After setup, verify protection is working:

```bash
# This should fail (cannot push to main directly)
git checkout main
echo "test" >> README.md
git commit -am "test direct commit"
git push origin main
# Expected: ERROR - protected branch hook declined
```

## CI Status Checks

The following jobs must pass:

1. **Lint** - Code formatting (black) and style (ruff)
2. **Test (Python 3.11)** - Full test suite on Python 3.11
3. **Test (Python 3.12)** - Full test suite on Python 3.12
4. **All checks passed** - Aggregates all job results

Each PR will show these checks at the bottom with pass/fail status.

## Workflow for Contributors

1. Create feature branch: `git checkout -b feature/my-feature`
2. Make changes and commit
3. Push branch: `git push origin feature/my-feature`
4. Open PR on GitHub
5. Wait for CI checks to pass
6. Request review
7. Address feedback
8. Merge after approval + passing checks

## Troubleshooting

**Q: CI checks not running?**
- Ensure workflow file is in `.github/workflows/ci.yml`
- Check Actions tab for errors
- Verify branch is not filtered in workflow `on:` section

**Q: Status checks not appearing in branch protection?**
- Status checks only appear after they've run at least once
- Push a PR to trigger the workflow first
- Then they'll be available in branch protection settings

**Q: Need to bypass for hotfix?**
- Don't. Instead, create an emergency branch protection policy
- Or temporarily add yourself to an exception list
- Always re-enable protection immediately after

## Related Files

- `.github/workflows/ci.yml` - CI workflow definition
- `pyproject.toml` - Tool configuration (black, ruff, pytest)
- `CONTRIBUTING.md` - Contributor guidelines
