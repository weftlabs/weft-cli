# Development Guide

This document describes how to develop and contribute to Weft.  
It is intended for contributors and maintainers, not end users.

## Getting Started

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git

### Development Setup

```bash
# Clone repository
git clone https://github.com/weftlabs/weft-cli.git
cd weft-cli

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
```

## Project Structure

```
weft/
├── src/weft/               # Main package
│   ├── agents/             # Agent implementations
│   ├── cli/                # CLI commands
│   ├── config/             # Configuration management
│   ├── git/                # Git operations
│   ├── history/            # AI history tracking
│   ├── templates/          # Docker & config templates
│   └── utils/              # Utilities
├── tests/                  # Test suite
│   ├── unit/               # Unit tests (mirror src structure)
│   └── integration/        # Integration tests
├── docs/                   # Documentation
├── templates/              # CLI templates
├── pyproject.toml          # Package configuration
└── README.md               # Project overview
```

## Code Style

### Python Style Guide

- Follow PEP 8
- Use type hints
- Keep functions short (<50 lines)
- Use descriptive names

**Docstrings:**

- Module-level: 1 sentence describing purpose
- Public functions: 1-2 lines max, only if intent not obvious
- NO Args/Returns/Raises sections
- NO examples in docstrings (use tests)

### Linting

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Run all checks
black src/ tests/ && ruff check src/ tests/ && mypy src/
```

## Testing

### Test Structure

Tests MUST mirror source structure:

```
src/weft/config/settings.py  →  tests/unit/weft/config/test_settings.py
src/weft/agents/meta.py      →  tests/unit/weft/agents/test_meta.py
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/weft/config/test_settings.py

# Run specific test function
pytest tests/unit/weft/config/test_settings.py::test_load_weftrc_valid_file
```

## Development Workflow

### 1. Choose a Feature

Check existing issues for priorities and planned features.

```bash
gh issue list
```

### 2. Create Feature Branch

```bash
git checkout -b feat/feature-name
# or for bugfix
git checkout -b fix/issue-description
```

### 3. Implement

- Write tests first (TDD) or alongside code
- Keep commits focused and logical
- Write clear commit messages
- Follow PEP 8 and type hints
- Update documentation for behavior changes

### 4. Test

```bash
pytest
black src/ tests/
ruff check src/ tests/
mypy src/
```

### 5. Document

- Update relevant docs in `docs/`
- Add docstrings if needed
- Update CHANGELOG.md

### 6. Submit PR

```bash
git push origin feat/feature-name
```

Then create a pull request on GitHub referencing the feature or issue, describing changes, including test results, and tagging reviewers.

## Commit Messages

Format: `type(scope): subject`

**Examples:**

```
feat(cli): add weft init command
fix(config): handle missing .weftrc.yaml gracefully
docs(guide): update getting started tutorial
test(agents): add meta agent integration tests
```

## Getting help

- Open a GitHub issue for bugs or unexpected behavior  
- Use pull requests for code changes

## Resources

- **Architecture:** [architecture.md](architecture.md)  
- **CLI Reference:** [cli-reference.md](cli-reference.md)  
- **Installation:** [installation.md](installation.md)
