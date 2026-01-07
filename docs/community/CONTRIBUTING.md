# Contributing

Thanks for your interest in contributing to Weft.

This document covers the basics for contributing code and documentation.  
For deeper system details, see the Development Guide.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git

### Setup Steps

1. **Clone repository:**
```bash
git clone https://github.com/weftlabs/weft-cli.git
cd weft-cli
```

2. **Create virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install in development mode:**
```bash
pip install -e ".[dev]"
```

4. **Run tests:**
```bash
pytest
```

## Code Style

### Python Style Guide

- Follow [PEP 8](https://pep8.org/)
- Use [Black](https://black.readthedocs.io/) for formatting
- Use [Ruff](https://github.com/charliermarsh/ruff) for linting
- Use type hints for all functions (optional to check with mypy)
- Write docstrings for all public APIs

### Docstring Format

- Module-level: 1 sentence describing purpose
- Public functions: 1-2 lines max, only if intent not obvious
- NO Args/Returns/Raises sections
- NO examples in docstrings (use tests instead)
- Prefer clear naming over verbose documentation

## Testing Requirements

### Writing Tests

- **Unit tests:** Test individual functions/classes  
- **Integration tests:** Test full workflows  
- **No network calls:** Mock external APIs

### Running Tests

```bash
# Run all tests
pytest

# Run specific test
pytest tests/unit/test_config.py -v

# Run integration tests only
pytest tests/integration/ -v
```

## Pull Request Process

### Before Submitting

1. **Create feature or fix branch:**
```bash
git checkout -b feat/your-feature-name
# or
git checkout -b fix/your-bugfix-name
```

2. **Make changes:**
- Write code
- Add tests
- Update documentation

3. **Run checks:**
```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Run tests
pytest

# (Optional) Check types
mypy src/
```

4. **Commit:**
```bash
git add .
git commit -m "feat: Add feature description"
```

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]

[optional footer]
```

**Types:**
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `test:` Adding tests
- `refactor:` Code refactoring
- `style:` Code style changes
- `chore:` Maintenance tasks

### Creating Pull Request

1. **Push branch:**
```bash
git push origin feat/your-feature-name
# or
git push origin fix/your-bugfix-name
```

2. **Open PR on GitHub**

3. **PR Checklist:**
- [ ] Tests pass
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Docstrings written

4. **Wait for review**

## CI/CD Checks

Pull requests are automatically checked by CI.  
Fix reported issues and push updates to your branch.

### After Review

- Address review comments  
- Push changes  
- Request re-review  

## Development Workflow

If you are adding new functionality, follow existing patterns and update tests and documentation accordingly.

## Resources

- [Development Guide](../development.md)  
- [Architecture](../architecture.md)  
- [CLI Reference](../cli-reference.md)

## Getting help

- Open a GitHub issue for bugs or questions  
- Check the documentation before opening a PR
