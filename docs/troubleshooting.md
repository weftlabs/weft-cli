# Troubleshooting

This page lists common issues and how to fix them.  
If something goes wrong, start here.

---

## Installation

### `weft` command not found

**Problem**  
The `weft` command is not available after installation.

**Fix**

```bash
weft --version
```

If the command is still not found, reinstall using your chosen method and ensure your PATH is set correctly.  
See: installation.md

---

### Import or module errors

**Problem**  
Python reports import or module errors when running Weft.

**Fix**

- Ensure Python 3.11+ is installed
- Reinstall Weft
- Avoid mixing system Python and virtual environments

```bash
python --version
```

---

## Configuration

### `.weftrc.yaml` not found

**Problem**  
Weft reports that configuration is missing.

**Fix**

```bash
weft init
```

Ensure you are running commands from the project root.

---

### API key not detected

**Problem**  
Weft reports that no API key is available.

**Fix**

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

Restart the runtime after setting the key:

```bash
weft down
weft up
```

---

### Invalid configuration

**Problem**  
Weft reports configuration or validation errors.

**Fix**

- Check YAML indentation (spaces only)
- Restore a clean config

```bash
mv .weftrc.yaml .weftrc.yaml.bak
weft init
```

---

## Docker

### Docker is not running

**Problem**  
Weft cannot connect to Docker.

**Fix**

- Start Docker Desktop (macOS / Windows)
- Start the Docker service (Linux)

```bash
docker ps
```

---

### Permission denied on Docker socket (Linux)

**Problem**  
Your user cannot access Docker.

**Fix**

```bash
sudo usermod -aG docker $USER
```

Log out and back in for changes to apply.

---

### Containers fail to start

**Problem**
Agent containers exit immediately.

**Fix**

```bash
weft logs meta
```

Most commonly caused by missing API keys or Docker misconfiguration.

---

## Runtime & agents

### Agents are not processing work

**Problem**  
Agents start but no output is produced.

**Fix**

- Ensure the runtime is running
- Restart the runtime

```bash
weft down
weft up
```

---

### Agent output is incorrect or incomplete

**Problem**  
Generated output does not match expectations.

**Fix**

- Refine the feature prompt
- Adjust agent prompts if needed
- Rerun the feature

Iteration is expected.

---

## Features & git

### Feature cannot be created or started

**Problem**  
Feature commands fail.

**Fix**

- Ensure the project is initialized
- Use a simple feature name (kebab-case)

```bash
weft feature list
```

---

### Merge fails due to untracked files

**Problem**  
Git reports that untracked files would be overwritten.

**Fix**

1. Move or commit the untracked file  
2. Retry the review

```bash
weft feature review <feature>
```

---

## Networking

### Cannot reach the AI provider

**Problem**  
Network errors or timeouts occur.

**Fix**

- Check internet connectivity
- Verify proxy or firewall settings
- Confirm the API endpoint is reachable

---

## Getting help

If the issue persists:

1. Check logs:
   ```bash
   weft logs meta --tail 100
   ```

2. Open a GitHub issue:  
   https://github.com/weftlabs/weft-cli/issues

Include:
- Weft version
- Operating system
- Docker version
- Error message

---
