# Release Guide

This document describes how maintainers create a new release of **Weft CLI**.

> This guide is for maintainers only. End users do not need it.

---

## Overview

Releases are created by:
1. Updating the version and changelog
2. Creating a git tag
3. Letting GitHub Actions build and publish artifacts

Most of the process is automated once the tag is pushed.

---

## One-time setup (Homebrew only)

If you publish via Homebrew:

- Create the tap repository: `weftlabs/homebrew-tap`
- Add a `HOMEBREW_TAP_TOKEN` GitHub Actions secret to `weftlabs/weft-cli`
  - Token must have write access to the tap repository
- Ensure the formula exists at `homebrew-tap/Formula/weft.rb`

This setup is required only once.

---

## Release checklist

### 1. Prepare `main`

```bash
git checkout main
git pull origin main
```

Ensure:
- Tests pass
- No local changes are pending

---

### 2. Run checks locally

```bash
pytest
ruff check .
black --check .
mypy src/
```

Fix any issues before continuing.

---

### 3. Update version and changelog

- Bump `version = "..."` in `pyproject.toml`
- Update `CHANGELOG.md` for the release

Do not include unreleased or speculative items.

---

### 4. Commit and tag

```bash
git add pyproject.toml CHANGELOG.md
git commit -m "chore(release): bump version to vX.Y.Z"
git push origin main

git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push origin vX.Y.Z
```

Pushing the tag triggers the release workflows.

---

### 5. Verify automation

In GitHub Actions, verify that:
- The release workflow completes successfully
- Artifacts are published
- Homebrew formula is updated (if enabled)

---

### 6. Smoke test installation

After the workflows complete:

```bash
brew tap weftlabs/tap
brew install weft
weft --version
```

Optionally test alternative install methods (pipx, install script).

---

## Troubleshooting

### Version mismatch

If the tag does not match `pyproject.toml`:

1. Delete the tag locally and remotely
2. Fix the version
3. Re-tag and push again

---

### Homebrew update failed

Most commonly caused by:
- Invalid or missing `HOMEBREW_TAP_TOKEN`
- Formula checksum mismatch

Check the Actions logs and rerun if needed.

---

## Notes

- Releases should always be created from `main`
- Avoid rewriting tags after publication
- Keep this document updated if the automation changes

---