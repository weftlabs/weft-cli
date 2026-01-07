---
hide:
  - navigation
  - toc
---

<div align="center" markdown>

# Weft CLI

**Structured AI workflows for real-world software development**

Design, implement, and review features with specialized AI agents — auditable, human-controlled, and ready for production use.

[Get Started](installation.md){ .md-button .md-button--primary }
[View on GitHub](https://github.com/weftlabs/weft-cli){ .md-button }

</div>

---

## What is Weft?

Weft is a developer-first CLI that uses specialized AI agents to build software features end-to-end — without giving up control.

Instead of ad‑hoc prompts or “vibe coding”, Weft provides a **repeatable, reviewable workflow** that fits into how real teams already work.

- **AI assists, humans decide**
- **Every step is auditable**
- **Nothing auto‑merges**
- **Built for real projects**

---

## Why teams use Weft

<div class="grid cards" markdown>

-   **Predictable, not opaque**

    ---

    Role‑based agents with clear responsibilities — no random prompts, no surprises.

-   **You stay in control**

    ---

    AI proposes changes. You review them. Nothing runs or merges without approval.

-   **Auditability by default**

    ---

    Every prompt, decision, and output is git‑tracked and reproducible.

-   **Fits existing workflows**

    ---

    Works with branches, reviews, CI, and existing repositories.

</div>

---

## How it works (high level)

Feature request → Agents → Human review → Merge

Weft runs a fixed sequence of agents that design, implement, and test a feature.  
Each step produces artifacts you can inspect, modify, or reject.

[See the full agent pipeline →](agents.md)

---

## Quick start

Get started in a few minutes:

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
```

👉 [Full installation guide →](installation.md)

---

## Built for quality and security

- No automatic code execution  
- No secrets or PII sent to AI  
- Mandatory human review gates  
- Containerized, isolated agents  
- Designed with common enterprise security requirements in mind  

[Learn more about the architecture →](architecture.md)

---

## Open source

Weft CLI is open source and MIT‑licensed.

- Report bugs or request features on GitHub
- Join discussions and help shape the roadmap
- Contributions are welcome

[View the repository →](https://github.com/weftlabs/weft-cli)

---

<div align="center" markdown>

**Ready to build with AI — without giving up control?**

[Get Started →](installation.md){ .md-button .md-button--primary }

</div>
