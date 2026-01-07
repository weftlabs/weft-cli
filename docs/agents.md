# Agents

Weft uses **specialized AI agents** to turn a feature request into reviewable, production-ready code — while keeping humans firmly in the loop.

Each agent has a **single, well-defined responsibility**. Agents run in a fixed sequence and produce artifacts you can inspect, edit, or reject.

---

## The agent workflow (conceptual)

Feature request  
→ Design  
→ Implementation  
→ Validation  
→ Human review  
→ Merge

Agents never merge code automatically. You stay in control at every decision point.

---

## Why agents (instead of prompts)?

Traditional AI coding tools rely on long, ad-hoc prompts and unpredictable outputs.

Weft agents are different:

- **Each agent has one job**
- **Inputs and outputs are explicit**
- **Results are reproducible**
- **Every step is git-tracked**

This makes AI-assisted development predictable, auditable, and suitable for real projects.

---

## The agents

### Meta (00)

**Purpose:** Understand the feature and produce a clear design brief.

**Outputs:**
- Feature summary
- User stories
- Acceptance criteria
- Constraints and assumptions

Use this agent to clarify *what* should be built before writing code.

---

### Architect (01)

**Purpose:** Design the technical solution.

**Outputs:**
- Data models
- API design
- Component boundaries
- Security and error-handling considerations

This agent focuses on *how* the feature should be implemented.

---

### OpenAPI (02)

**Purpose:** Generate an explicit API contract.

**Outputs:**
- OpenAPI (Swagger) specifications
- Schemas and endpoint definitions

This creates a shared source of truth for backend and frontend work.

---

### UI (03)

**Purpose:** Generate user interface components.

**Outputs:**
- Page-level components
- Feature-specific UI components
- Reusable UI elements

The UI agent consumes the API and architecture outputs.

---

### Integration (04)

**Purpose:** Connect everything together.

**Outputs:**
- API clients
- Service layers
- Data-fetching logic
- Error handling

This agent wires the UI and backend together in a type-safe way.

---

### Test (05)

**Purpose:** Validate the feature.

**Outputs:**
- Unit tests
- Integration tests
- Test execution results

Tests are generated and executed automatically, but failures never merge silently.

---

## Human review model

Weft enforces a single, explicit human review gate.

After all agents finish:

- Review the generated files
- Inspect diffs in the feature branch
- Check test results
- Decide to accept, modify, or discard the feature

Run:

```bash
weft feature review <feature>
```

Nothing is merged without this step.

---

## Agent ordering

Agents are designed to run sequentially:

1. Meta
2. Architect
3. OpenAPI
4. UI
5. Integration
6. Test

You can disable agents or stop early if a design needs revision.

---

## When to stop and iterate

Stop the workflow when:
- Requirements are unclear
- Architecture doesn’t feel right
- Generated code needs direction changes

Refine the prompt, then rerun the agent. Iteration is expected.

Stopping early is a feature, not a failure.

---

## What this page intentionally omits

This page focuses on **how to think about agents**, not how they are implemented.

For deeper details, see:
- Configuration → configuration.md
- Architecture → architecture.md
- CLI commands → cli-reference.md

---

## Next steps

- Learn how to configure agents → configuration.md
- See agent-related CLI commands → cli-reference.md

---