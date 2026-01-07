# Weft CLI

**Structured AI workflows for real-world software development**

Weft is a developer-first CLI that uses specialized AI agents to help you design, implement, and review software features — while keeping humans firmly in control.

Instead of ad-hoc prompts or “vibe coding”, Weft provides a **repeatable, auditable workflow** that fits naturally into existing development processes.

---

## What Weft is (and isn’t)

**Weft is:**
- A CLI for structured, AI-assisted feature development
- Built around explicit steps and human review
- Designed for real projects and real teams
- Auditable by default

**Weft is not:**
- An auto-merge coding bot
- A chat interface for prompts
- A replacement for code review or CI

---

## How it works (high level)

Feature request  
→ Agents  
→ Human review  
→ Merge

Each agent has a single responsibility (design, architecture, implementation, validation).  
All outputs are written to disk and reviewed before anything is merged.

---

## Quick start

Install Weft:

```bash
brew install weft
```

Initialize it in your project:

```bash
weft init
weft up
```

Create and run a feature:

```bash
weft feature create user-auth
weft feature start user-auth
weft feature review user-auth
```

For full installation instructions and alternatives, see the docs.

---

## Documentation

Start here:

- **Installation** → docs/installation.md  
- **Agents** → docs/agents.md  
- **Configuration** → docs/configuration.md  
- **CLI reference** → docs/cli-reference.md  
- **Architecture** → docs/architecture.md  
- **Troubleshooting** → docs/troubleshooting.md  

---

## Project status

Weft is in **early development (v0.x)**.

The core workflow is functional, but APIs and behavior may change before 1.0.  
Feedback and experimentation are welcome.

---

## Contributing

Contributions are welcome.  
See docs/development.md for setup and guidelines.

---

## License

MIT License. See LICENSE for details.

---

## Support

- GitHub Issues: https://github.com/weftlabs/weft-cli/issues

---
