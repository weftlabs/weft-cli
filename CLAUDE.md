# AI-Assisted Feature Development Workflow

## Project Overview

This is an enterprise-grade, security-aware, and fully auditable workflow system for AI-assisted software development.
It orchestrates role-based AI agents through Git worktrees, file-based task queues, and strict audit trails.

**Key Characteristics:**

- Production-ready with Docker deployment
- SOC2/ISO27001 compliant
- Supports online, hybrid, and fully offline operation
- Human-in-the-loop with mandatory review gates
- Full observability with OpenTelemetry

## Project Structure

```
weft/
├── docs/                          # All documentation
│   ├── index.md                  # Documentation home
│   ├── installation.md           # Installation guide
│   ├── cli-reference.md          # Complete CLI documentation
│   ├── architecture.md           # Technical architecture
│   ├── agents.md                 # Agent specifications
│   ├── configuration.md          # Configuration guide
│   ├── development.md            # Development guide
│   └── troubleshooting.md        # Common issues and solutions
├── src/                          # Application code
│   └── weft/                     # Main package
│       ├── agents/               # Agent implementations
│       ├── cli/                  # CLI commands
│       ├── config/               # Configuration management
│       ├── git/                  # Git operations
│       ├── queue/                # Task queue operations
│       ├── state/                # Feature state management
│       └── watchers/             # Agent watchers
├── tests/                        # Test suites
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
├── prompt-specs/                 # Agent prompt specifications
├── templates/                    # CLI templates
├── docker/                       # Docker configurations
├── README.md                     # Project entry point
└── LICENSE                       # MIT License
```

## Core Concepts

### Role-Based AI Agents (MPCs)

The system uses 6 specialized AI agents:

| Agent            | Responsibility                                         |
|------------------|--------------------------------------------------------|
| 00 Meta          | Feature understanding, design brief, prompt generation |
| 01 Architect     | Domain modeling, use cases, API needs                  |
| 02 OpenAPI       | Specification creation and validation                  |
| 03 UI Skeleton   | Layout and component scaffolding                       |
| 04 Integration   | API wiring and state management                        |
| 05 Test & Review | Test generation and code risk review                   |

Each agent:

- Runs in a dedicated Git worktree
- Uses versioned prompt specifications (semver)
- Has isolated input/output directories
- Produces auditable artifacts

### Architecture Pattern: File-Based Task Queues

```
my-app-ai-history/FEAT-123/
  01-architect/
    in/           # Input prompts (*.md)
    out/          # AI outputs (*_result.md)
    log/          # Processing logs
```

Watcher scripts monitor `in/` directories and:

1. Process new `.md` files
2. Call AI backend (Claude, local LLM, or gateway)
3. Write results to `out/`
4. Rename input to `.processed`

### Git Worktree Strategy

Each feature gets:

- A dedicated branch
- A dedicated worktree directory
- Isolated dependencies and state
- Parallel development capability

## Development Guidelines

### Mandatory Engineering Workflow (Enforced)

For every code modification (feature, refactor, or fix), the following workflow is mandatory:

1. Make the smallest possible change that satisfies the requirement.
2. Add or update tests covering the change.
3. Run the FULL test suite.
   - If any test fails, the change is incomplete.
4. Run all configured linters and formatters.
5. Update documentation if behavior, interfaces, configuration, or workflows changed.

Exceptions are not allowed unless explicitly documented in the related story or commit message.

### Coding Style & Linting (STRICT)

Weft is a **CLI-first product**, not a public Python SDK.  
Code is written for **senior engineers**, not for teaching or onboarding beginners.

#### General Principles
- Prefer **clear structure and naming** over comments
- Avoid redundancy: do not explain what the code already expresses
- Assume Python, typing, and tooling knowledge
- Favor readability of the file over completeness of inline documentation

#### Python Docstring Policy (Mandatory)

Docstrings are intentionally minimal.

**Allowed**
- One short **module-level docstring** (1 sentence, intent only)
- One short docstring for **public functions only if intent is not obvious**
- Docstrings must be **1–2 lines max**
- Describe *why*, not *what*

**Forbidden**
- `Args:`, `Returns:`, `Raises:` sections
- `Example:` blocks or doctest-style snippets
- Multi-paragraph docstrings
- Obvious explanations (e.g. “Generate SHA256 hash”)
- Teaching-style comments

If unsure whether a docstring is needed: **omit it**.

#### Comments
- Do not restate the code in comments
- Use comments only for:
  - non-obvious decisions
  - edge cases
  - intentional constraints
- Prefer expressive naming over comments

#### Tests
- Behavioral examples belong in **tests**, not in docstrings
- If an example is useful, write a pytest

#### Linting Expectations
- Python: `ruff` + `black`
- No unused imports, variables, or dead code
- Functions should remain short and focused
- Prefer explicit over clever code

Violations of this section should be treated as **style regressions** during review.

#### Type Safety & Static Analysis

- All new or modified Python code MUST include type hints.
- Public APIs and CLI interfaces require explicit typing.
- Prefer gradual strictness using mypy or pyright.
- Type errors are treated as correctness issues, not style issues.

### When Adding New Features

1. **Documentation First** - All features must be documented in `docs/`
2. **Security by Design** - Never expose secrets, PII, or production data to AI
3. **Audit Trail** - All AI interactions must be versioned and traceable
4. **Human Review** - AI output never auto-merges, always requires approval

### Code Style

### Dependency & Change Hygiene

- Do not introduce new dependencies without strong justification.
- Every dependency addition or upgrade must be documented.
- Lockfiles must be updated consistently.
- Breaking changes require:
  - Documentation updates
  - Migration notes
  - Explicit mention in commit messages and story acceptance criteria

- **Python**: Follow PEP 8, use type hints
- **Shell**: Shellcheck compliant, use `set -e`
- **Docker**: Multi-stage builds, non-root users, minimal base images

### Testing Philosophy

### Test Execution Policy

- The full test suite MUST be executed after every non-trivial change.
- Tests must be deterministic and runnable on a clean checkout.
- Slow tests must be categorized, but CI MUST still execute the full suite.
- Failing tests are blocking defects and must not be deferred.

- Unit tests for all agent logic
- Integration tests for watcher orchestration
- End-to-end tests for full feature flows
- Security tests for prompt injection scenarios

**Test Directory Structure:**

Tests MUST mirror the source code structure to maintain clarity and discoverability:

```
src/weft/
├── agents/
├── ai/
├── cli/
├── config/
└── ...

tests/unit/weft/
├── agents/
├── ai/
├── cli/
├── config/
└── ...
```

**Rules:**
- Unit tests go in `tests/unit/weft/{module}/` mirroring `src/weft/{module}/`
- Integration tests go in `tests/integration/` (no mirroring required, organized by workflow)
- Test file naming: `test_{source_file}.py` tests `{source_file}.py`
- Each test directory MUST have `__init__.py`

**Example:**
- Source: `src/weft/config/settings.py`
- Tests: `tests/unit/weft/config/test_settings.py`

## Key Files to Understand

### Documentation (Read First)

1. **docs/index.md** - Documentation home and system overview
2. **docs/architecture.md** - Technical architecture and agent model
3. **docs/installation.md** - Installation and quick start guide
4. **docs/cli-reference.md** - Complete CLI command documentation
5. **docs/agents.md** - Agent specifications and behavior

### Additional Documentation

- **docs/configuration.md** - Configuration guide and options
- **docs/development.md** - Development setup and guidelines
- **docs/troubleshooting.md** - Common issues and solutions

## Common Tasks

### Creating a New Agent

1. Define agent responsibility in architecture docs
2. Create prompt specification in `prompt-spec/vX.Y.Z/`
3. Implement watcher with OpenTelemetry tracing
4. Add Docker service definition
5. Update documentation

### Adding Observability

All agent code should include:

- Span creation for major operations
- Metrics for success/failure counts
- Duration histograms
- Error attributes on failures

Example:

```python
with tracer.start_as_current_span("agent.process") as span:
    span.set_attribute("agent.id", agent_id)
    span.set_attribute("feature.id", feature_id)
    # ... processing logic
    span.set_attribute("status", "success")
```

### Security Considerations

**Always:**

- Validate and sanitize all inputs
- Use read-only mounts for code repositories
- Run containers with non-root users
- Hash all prompts and outputs
- Log all AI interactions

**Never:**

- Execute AI-generated code automatically
- Include real customer data in prompts
- Store API keys in code or configs
- Auto-merge AI outputs
- Skip human review gates

## Deployment Models

### Local Development

- Single machine
- iTerm2 automation
- Claude API online
- Manual orchestration

### Team Deployment

- Docker Compose
- Shared AI history repo
- OpenTelemetry collector
- Grafana dashboards

### Enterprise

- Kubernetes
- Claude Gateway Proxy
- Full observability stack
- Compliance audit trails

### Air-Gapped

- Local LLM (Ollama)
- No external network
- Full sovereignty
- Offline operation

## Testing Strategy

### Unit Tests

- Agent watcher logic
- Prompt parsing
- Output formatting
- Hash generation

### Integration Tests

- Watcher → AI backend flow
- Git operations
- Docker container interactions
- OpenTelemetry export

### Security Tests

- Prompt injection attempts
- Secret exposure detection
- Container escape attempts
- Audit trail verification

### End-to-End Tests

- Full feature pipeline
- Multi-agent coordination
- Human review gates
- Rollback scenarios

## Troubleshooting

### Watcher Not Processing Files

Check:

1. File permissions on `in/` directory
2. Watcher process is running (`docker-compose ps`)
3. Log output (`docker-compose logs watcher-{agent}`)
4. AI backend connectivity

### Docker Container Fails to Start

Check:

1. Volume mounts exist and are accessible
2. Environment variables are set
3. Port conflicts
4. Resource limits (CPU/memory)

### OpenTelemetry Not Reporting

Check:

1. OTEL collector is running
2. OTEL endpoint configuration
3. Network connectivity to collector
4. Span export errors in logs

## Important Conventions

### Naming

- Features: `feat/feature-name`
- Agent IDs: `01-architect`, `02-openapi`, etc.
- Prompt files: `{feature}_prompt_v{revision}.md`
- Output files: `{prompt-stem}_result.md`

### Versioning

- Prompt specs: Semantic versioning (MAJOR.MINOR.PATCH)
- Docker images: Git SHA + semantic version
- API compatibility: Follow semver strictly

### Commit Messages

- Format: `{type}({scope}): {subject}`
- Types: feat, fix, docs, chore, refactor, test
- Scope: agent name, component, or module
- **Do NOT include AI co-author attribution** (e.g., no `Co-Authored-By: Claude`)
- Examples:
    - `feat(watcher): add retry logic for failed AI calls`
    - `docs(deployment): update Docker compose example`
    - `fix(architect): handle empty prompt files`

## External Dependencies

### Required

- Git
- Docker & Docker Compose
- Python 3.11+

### Optional (by deployment model)

- iTerm2 (macOS automation)
- Claude API key (online mode)
- Ollama (offline mode)
- Kubernetes (enterprise)

## Performance Considerations

- Watchers poll every 2 seconds (configurable)
- Docker containers have resource limits
- OpenTelemetry batches every 10 seconds
- Git worktrees share object database (efficient)

## Useful Commands

```bash
# View all services
docker-compose ps

# Follow logs for specific agent
docker-compose logs -f watcher-architect

# Restart a service
docker-compose restart watcher-architect

# View OpenTelemetry metrics
curl http://localhost:8889/metrics

# Check Git worktrees
git worktree list

# View AI history
cd ../my-app-ai-history && git log --oneline
```

## Current Development Model

Weft uses a **CLI-driven feature workflow** for development:

1. Create features using `weft feature create <feature-name>`
2. Define specifications interactively with Agent 00 (Meta)
3. Run agent pipeline with `weft feature start <feature-name>`
4. Review outputs with `weft feature review <feature-name>`
5. Accept or iterate based on results

**Automated Agent Pipeline:**

Running `weft feature start` executes all 6 agents sequentially:
- **Agent 00 (Meta)** - Analyzes feature request, generates design brief
- **Agent 01 (Architect)** - Designs technical architecture and data models
- **Agent 02 (OpenAPI)** - Generates complete OpenAPI/Swagger specs
- **Agent 03 (UI)** - Creates React/TypeScript component implementations
- **Agent 04 (Integration)** - Generates API clients, hooks, state management
- **Agent 05 (Test)** - Writes comprehensive test suites

Code Generation Format:
```typescript
```typescript path=src/components/UserCard.tsx action=create
import { User } from '../types/api';
// ... complete implementation
```
```

Code is automatically:
- Extracted from markdown code blocks with `path=` metadata
- Applied to feature branch worktree
- Staged in git for review

Human review gate at `weft feature review` before merging to main.

## Automation vs Documentation Contract

The following responsibilities are explicitly separated:

Handled by documentation (this file):
- Architectural and design principles
- Coding philosophy and trade-offs
- Decision-making guidelines
- When and why to write tests and documentation

Handled by automation (hooks / CI):
- Code formatting
- Lint enforcement
- Test execution
- Coverage thresholds
- Type checking

Critical quality rules MUST be enforced by tooling whenever possible.
Documentation exists to explain intent, not to replace enforcement.

## Contributing

**Before Contributing:**
1. Read `docs/development.md` for development setup and guidelines
2. Check existing issues and documentation before starting
3. Follow the CLI-driven workflow for feature development

**All Contributions Must:**
- Follow the mandatory engineering workflow (tests, linters, documentation)
- Achieve 90%+ test coverage for new code
- Include documentation updates for behavior changes
- Follow security guidelines (no secrets, mandatory review)
- Pass all CI checks before merging
