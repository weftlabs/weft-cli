# CLI Reference

Reference for all available `weft` commands and options.  
This page is intentionally concise and assumes basic familiarity with Weft concepts.

## Global flags

These flags apply to all commands:

```bash
weft [GLOBAL FLAGS] COMMAND [COMMAND OPTIONS]
```

| Flag              | Description           |
|-------------------|-----------------------|
| `--config PATH`   | Config file path (default: `.env`) |
| `--verbose, -v`   | Enable verbose output  |
| `--version`       | Show version and exit  |
| `--help`          | Show help and exit     |

## Commands Overview

| Command         | Description                |
|-----------------|----------------------------|
| `weft init`     | Initialize a Weft project  |
| `weft up`       | Start Docker runtime       |
| `weft down`     | Stop Docker runtime        |
| `weft logs`     | View agent watcher logs    |
| `weft feature`  | Manage feature lifecycle   |

---

## `weft init`

Initialize Weft in the current directory.

### Synopsis

```bash
weft init [OPTIONS]
```

### Options

| Flag                      | Type    | Description               |
|---------------------------|---------|---------------------------|
| `--project-name TEXT`      | String  | Project name              |
| `--project-type CHOICE`    | Choice  | `backend` \| `frontend` \| `fullstack` |
| `--ai-provider CHOICE`     | Choice  | `claude` \| `ollama` \| `other` |
| `--ai-history-path PATH`   | Path    | AI history repo path      |
| `--model TEXT`             | String  | AI model (e.g., `claude-3-5-sonnet-20241022`) |

### Exit Codes

| Code | Meaning                       |
|------|-------------------------------|
| 0    | Success                      |
| 1    | Error (e.g., missing deps)   |

### Examples

```bash
weft init
```

```bash
weft init --project-name my-app --project-type fullstack --ai-provider claude --ai-history-path ../weft-ai-history --model claude-3-5-sonnet-20241022
```

---

## `weft up`

Start the Docker runtime environment.

### Synopsis

```bash
weft up [OPTIONS]
```

### Options

| Flag                   | Type | Default | Description              |
|------------------------|------|---------|--------------------------|
| `--detach, -d`          | Flag | true    | Run containers in background |
| `--no-detach, -D`       | Flag | -       | Run containers in foreground  |

### Environment Variables

| Variable               | Description                  |
|------------------------|------------------------------|
| `ANTHROPIC_API_KEY` or `WEFT_ANTHROPIC_API_KEY` | Claude API key (required) |
| `AI_BACKEND`           | Override backend from config |
| `CLAUDE_MODEL`         | Override model from config   |

### Exit Codes

| Code | Meaning                     |
|------|-----------------------------|
| 0    | Services started successfully |
| 1    | Docker not available or startup failed |

### Examples

```bash
weft up
```

```bash
CLAUDE_MODEL=claude-3-opus-20240229 weft up --no-detach
```

---

## `weft down`

Stop the Docker runtime environment.

### Synopsis

```bash
weft down [OPTIONS]
```

### Options

| Flag              | Type | Description           |
|-------------------|------|-----------------------|
| `--volumes, -v`   | Flag | Remove named volumes   |

### Exit Codes

| Code | Meaning                    |
|------|----------------------------|
| 0    | Services stopped successfully |
| 1    | Docker not available or stop failed |

### Examples

```bash
weft down --volumes
```

---

## `weft logs`

View logs from agent watcher containers.

### Synopsis

```bash
weft logs [AGENT] [OPTIONS]
```

### Arguments

| Argument | Description                   |
|----------|-------------------------------|
| `AGENT`  | Agent name (optional): `meta`, `architect`, `openapi`, `ui`, `integration`, `test` |

### Options

| Flag                 | Type    | Default | Description              |
|----------------------|---------|---------|--------------------------|
| `--follow, -f`       | Flag    | false   | Stream logs live         |
| `--tail, -n NUM`     | Integer | 100     | Number of lines to show  |

### Exit Codes

| Code | Meaning                    |
|------|----------------------------|
| 0    | Logs displayed (or interrupted) |
| 1    | Docker not available or container not found |

### Examples

```bash
weft logs meta --follow
```

---

## `weft feature`

Manage feature lifecycle.

### Synopsis

```bash
weft feature SUBCOMMAND [OPTIONS]
```

### Subcommands

| Subcommand | Description            |
|------------|------------------------|
| `create`   | Create a new feature   |
| `start`    | Start working on feature |
| `list`     | List features         |
| `status`   | Show feature status    |
| `review`   | Review feature outputs (accept/continue/drop) |
| `drop`     | Drop a feature        |

---

## `weft feature create`

Create a new feature.

### Synopsis

```bash
weft feature create FEATURE_NAME [OPTIONS]
```

### Arguments

| Argument      | Description          |
|---------------|----------------------|
| `FEATURE_NAME` | Feature name (kebab-case) |

### Options

| Flag                 | Type    | Description        |
|----------------------|---------|--------------------|
| `--description TEXT` | String  | Feature description |
| `--priority CHOICE`  | Choice  | `low` \| `medium` \| `high` |

### Exit Codes

| Code | Meaning                      |
|------|------------------------------|
| 0    | Feature created successfully |
| 1    | Feature exists or creation failed |

### Examples

```bash
weft feature create user-authentication --description "Add JWT auth" --priority high
```

---

## `weft feature start`

Start working on a feature.

### Synopsis

```bash
weft feature start FEATURE_NAME
```

### Arguments

| Argument      | Description        |
|---------------|--------------------|
| `FEATURE_NAME` | Feature to start   |

### Exit Codes

| Code | Meaning                  |
|------|--------------------------|
| 0    | Feature started          |
| 1    | Feature not found or already started |

---

## `weft feature list`

List features.

### Synopsis

```bash
weft feature list [OPTIONS]
```

### Options

| Flag                 | Type    | Description        |
|----------------------|---------|--------------------|
| `--status CHOICE`    | Choice  | Filter by status: `pending`, `in-progress`, `completed`, `dropped` |

### Examples

```bash
weft feature list --status in-progress
```

---

## `weft feature status`

Show feature status.

### Synopsis

```bash
weft feature status FEATURE_NAME
```

### Arguments

| Argument      | Description        |
|---------------|--------------------|
| `FEATURE_NAME` | Feature to show    |

### Examples

```bash
weft feature status user-authentication
```

---

## `weft feature review`

Review feature outputs and decide next step.

### Synopsis

```bash
weft feature review FEATURE_NAME [OPTIONS]
```

### Arguments

| Argument      | Description        |
|---------------|--------------------|
| `FEATURE_NAME` | Feature to review  |

### Options

| Flag                 | Description                      |
|----------------------|---------------------------------|
| `--delete-history`   | Delete AI history when dropping  |
| `--reason TEXT`      | Reason for dropping (audit)      |
| `--base-branch TEXT` | Target branch for merge (default: main) |

### Exit Codes

| Code | Meaning                      |
|------|------------------------------|
| 0    | Review completed             |
| 1    | Feature not found or cancelled |

### Outcomes

- **Accept:** Merge feature and mark completed  
- **Continue:** Keep feature active  
- **Drop:** Abandon feature and optionally delete history  

---

## `weft feature drop`

Drop a feature.

### Synopsis

```bash
weft feature drop FEATURE_NAME [OPTIONS]
```

### Arguments

| Argument      | Description        |
|---------------|--------------------|
| `FEATURE_NAME` | Feature to drop    |

### Options

| Flag                 | Short | Type  | Description                          |
|----------------------|-------|-------|------------------------------------|
| `--delete-history`   |       | Flag  | Permanently delete AI history       |
| `--reason`           | `-r`  | String| Reason for dropping (audit)         |
| `--force`            | `-f`  | Flag  | Skip confirmation                   |

### Exit Codes

| Code | Meaning                    |
|------|----------------------------|
| 0    | Feature dropped            |
| 1    | Feature not found or failed|

---

## Environment variables

Environment variables are documented in configuration.md.

---

## Configuration Files

Configuration resolution is documented in configuration.md.

---

## Shell Completion

Weft supports shell completion for Bash, Zsh, and Fish.

### Bash

```bash
# Add to ~/.bashrc
eval "$(_WEFT_COMPLETE=bash_source weft)"
```

### Zsh

```bash
# Add to ~/.zshrc
eval "$(_WEFT_COMPLETE=zsh_source weft)"
```

### Fish

```bash
# Add to ~/.config/fish/completions/weft.fish
eval (env _WEFT_COMPLETE=fish_source weft)
```

---

## See Also

- [Installation Guide](installation.md)  
- [Configuration Reference](configuration.md)  
- [Agent System](agents.md)  
- [Architecture](architecture.md)
