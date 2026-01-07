# Architecture

This page explains **how Weft is put together** and why it is designed the way it is.

Weft is a CLI that orchestrates **isolated agent runtimes** and produces **reviewable artifacts** in your repository. The design goal is simple:

> Make AI-assisted development **predictable, auditable, and safe** for real projects.

---

## High-level model

Weft separates your world into three clearly defined areas:

1. **Your code** (your git repository)
2. **Runtime & prompts** (Weft’s `.weft/` directory)
3. **AI history** (a git-tracked record of inputs/outputs)

Agents read explicit inputs, generate explicit outputs, and nothing is merged automatically.

---

## Where files live

### Project repository

Your normal project stays unchanged:

- `src/`, `app/`, `packages/`, etc. (your code)
- `.weftrc.yaml` (Weft configuration)
- `.weft/` (Weft runtime directory)

### Weft runtime directory: `.weft/`

`.weft/` is intentionally local to the project and safe to inspect:

- `docker-compose.yml` (agent runtime)
- `features/` (feature workspaces and state)
- `prompts/` (prompt specifications)
- `tasks/` and `history/` (run artifacts and metadata)

Most teams can keep `.weft/` committed to the repo (except secrets, which never belong there).

### AI history (separate git repo)

Weft can store AI artifacts in a dedicated history repository. This keeps AI traces auditable without polluting your main code history.

Typical contents:
- agent inputs (what was asked)
- agent outputs (what was produced)
- logs (what happened)

If you prefer a single-repo setup, you can also keep history inside the project — the key point is that it is **versioned and reviewable**.

---

## Why Docker

Agents run in containers to provide:

- **consistent environments** across machines
- **isolation** from your host
- predictable dependencies and tooling
- clearer security boundaries

Weft uses Docker Compose so every project can run its own agent runtime without conflicts.

---

## Git integration and isolation

Weft is built around git-native workflows:

- Each feature runs in its own **worktree**
- Outputs become regular diffs you can inspect
- You merge using your normal review process

This lets teams use AI assistance without changing how they do code review, CI, or releases.

---

## Key design decisions

### Human review gate

Weft enforces a single rule:

> AI can propose changes. Humans decide what ships.

Nothing auto-merges. You can always stop, adjust, or discard a feature.

### Explicit inputs and outputs

Weft avoids “hidden context”:

- prompts are visible
- outputs are written to disk
- artifacts are git-tracked

This makes the workflow repeatable and debuggable.

### Separation of code and AI artifacts

Weft keeps AI traces separate from your code by default, so you can:
- audit what happened
- share history safely (when appropriate)
- keep your main repository clean

---

## Security principles

Weft is built with conservative defaults:

- API keys live in **environment variables**, not config files
- Agents never execute code automatically
- You choose what is sent to an LLM
- Diffs and artifacts are reviewable before merging

If you need stricter controls (e.g., regulated environments), you can run with local models and restricted network access.

---

## What happens during a feature run (simplified)

1. You create a feature and start it
2. Weft runs agents in order (meta → architect → … → test)
3. Agents write artifacts and proposed code changes
4. You review diffs and decide what to accept
5. If accepted, you merge like any normal change

For the conceptual workflow, see: [Agents →](agents.md)

---

## Next steps

- Configure providers, models, and agents → configuration.md
- Learn the agent workflow → agents.md
- See all commands → cli-reference.md

---
