# Configuration

Weft is designed to work well **out of the box**.  
Most teams only need a minimal configuration and can rely on sensible defaults.

Configuration lives in a single file: **`.weftrc.yaml`**, created when you run `weft init`.

---

## The configuration model

Think of Weft configuration in four layers:

1. **Project context** – what kind of project this is  
2. **AI setup** – which model and provider to use  
3. **Agents** – which steps run in the workflow  
4. **Git & paths** – how Weft integrates with your repo  

If you understand these four, you understand Weft configuration.

---

## Minimal configuration (recommended)

Most projects work with something this simple:

```yaml
project:
  name: my-app
  type: fullstack

ai:
  provider: anthropic
  model: claude-3-5-sonnet-20241022

agents:
  enabled:
    - meta
    - architect
    - openapi
    - ui
    - integration
    - test
```

Everything else has safe defaults.

---

## Project

Defines what you are building.

```yaml
project:
  name: my-app
  type: fullstack
```

- **name**  
  Used for logs, feature metadata, and history tracking.

- **type**  
  One of:
  - `backend`
  - `frontend`
  - `fullstack`

This helps agents generate more appropriate output.

---

## AI configuration

Controls which LLM Weft uses and how.

```yaml
ai:
  provider: anthropic
  model: claude-3-5-sonnet-20241022
  model_profile: standard
```

### Provider

Supported providers:
- `anthropic` (default)
- `openai`
- `local`

### Model profiles

Model profiles trade speed for quality:

- `fast` – quicker, cheaper iterations
- `standard` – balanced default
- `quality` – slower, higher reasoning depth

Most teams should stick with `standard`.

---

## Agents

Agents run sequentially and can be enabled or disabled.

```yaml
agents:
  enabled:
    - meta
    - architect
    - openapi
    - ui
    - integration
    - test
```

Valid agents:
- `meta`
- `architect`
- `openapi`
- `ui`
- `integration`
- `test`

### Disabling agents

You can temporarily disable agents when iterating on design:

```yaml
agents:
  enabled:
    - meta
    - architect
```

This lets you stop before code generation.

---

## Git integration

Weft works directly with your git repository.

```yaml
git:
  worktree:
    base_branch: main
    prefix: feat/
```

- **base_branch**  
  Branch new features are created from.

- **prefix**  
  Naming convention for feature branches.

Each feature runs in its own isolated worktree.

---

## Paths and runtime files (advanced)

By default, Weft keeps all runtime data inside `.weft/`.

```yaml
paths:
  root: .weft
  features: .weft/features
  tasks: .weft/tasks
  history: .weft/history
```

You usually don’t need to change these unless:
- you have monorepo constraints
- you want to store history outside the repo

---

## Environment variables

Some settings are intentionally kept out of config files.

### Required

```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### Optional overrides

```bash
AI_BACKEND=anthropic
CLAUDE_MODEL=claude-3-5-sonnet-20241022
```

Environment variables always override `.weftrc.yaml`.

---

## Security principles

Weft follows a few strict rules:

- API keys are **never** stored in config files
- No secrets are sent to AI unless explicitly referenced
- All AI interactions are logged and reviewable
- Nothing is executed or merged automatically

This makes configuration safe to commit.

---

## Customizing agent prompts (advanced)

Agent prompts live under:

```
.weft/prompts/v1.0.0/
```

You can edit these to:
- adapt tone
- add project-specific rules
- experiment with workflows

After editing prompts, restart the runtime:

```bash
weft down
weft up
```

---

## When to change configuration

Change config when:
- switching models or providers
- adjusting workflow depth
- integrating into CI or monorepos

Avoid changing config for one-off features — prompts are usually the better lever.

---

## Next steps

- Learn how agents work → agents.md
- Explore CLI commands → cli-reference.md
- Understand the system design → architecture.md

---
