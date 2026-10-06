# weft-cli

## Purpose

Command-line client for the Weft buyer runtime. The npm package name is `@weftlabs/cli`. This repo also ships the MCP bundle in `mcpb/` and the vendored `weft` Skill in `skills/`.

## Stack

- Node >= 18, pnpm, TypeScript, tsup, Vitest, ESLint, Prettier.
- Runtime dependency: published `@weftlabs/sdk`. Not a workspace link.
- Mise owns Node, pnpm, and lefthook.

## Commands

```sh
mise install
mise exec -- pnpm install --frozen-lockfile
mise exec -- pnpm run lint:check
mise exec -- pnpm run format:check
mise exec -- pnpm run typecheck
mise exec -- pnpm run build
mise exec -- pnpm run test:unit
mise exec -- node scripts/test-packed-artifact.mjs
```

If pre-commit / pre-push hooks exist, they run automatically. Do not skip them with `--no-verify`.

## Repo-Specific Constraints

- Import only public `@weftlabs/sdk` exports. Do not import a deep path.
- Never edit the vendored Skill under `skills/weft/`. Change it in `weftlabs/skills`, then re-vendor it. `skills/SKILLS_REF` pins the commit.
- The version bump lands through a normal pull request. `sdk-follow.yml` may open or update `bot/cli-follow-sdk-<version>`. It does not push to `main`, create a tag, or merge. A breaking SDK line (a major change, or a minor change while the SDK is `0.x`) uses the title and label `breaking SDK line`. Releases are tag-driven: a `v*` tag on `main` runs `.github/workflows/release.yml`. That workflow does not push to `main`. If that tag exists and npm does not have the version, `sdk-follow.yml` dispatches the release again.

## PR Rules

- Branch from `main`. Open pull requests against `main`.
- Required checks must pass before merge.
- Patrick is the sole reviewer. Do not self-merge.

## Where to Look Next

- **Repo-internal context:** `README.md` and `docs/`
- **Cross-repo context (when checked out as part of `weft-dev`):** `../cto-os/`
- **Single-repo checkout:** this file plus `docs/` is the full picture; cross-repo context is unavailable, so scope work to what this repo owns.

## Related

- `docs/README.md` — map of this repo's docs folder
- `README.md` — install, bootstrap, and fetch result contract
- `docs/contract.md` — CLI command contract
