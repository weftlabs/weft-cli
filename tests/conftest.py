"""Pytest configuration and common fixtures for AI Workflow tests."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_code_repo(temp_dir: Path) -> Path:
    """Create a mock code repository directory."""
    repo_path = temp_dir / "code-repo"
    repo_path.mkdir(parents=True, exist_ok=True)
    return repo_path


@pytest.fixture
def mock_ai_history_repo(temp_dir: Path) -> Path:
    """Create a mock AI history repository directory with git initialized."""
    import subprocess

    history_path = temp_dir / "ai-history"
    history_path.mkdir(parents=True, exist_ok=True)

    # Initialize as git repository
    subprocess.run(
        ["git", "init"],
        cwd=history_path,
        capture_output=True,
        check=True,
    )

    return history_path


@pytest.fixture
def sample_config(mock_code_repo: Path, mock_ai_history_repo: Path) -> dict[str, str]:
    """Provide sample configuration values."""
    return {
        "CODE_REPO_PATH": str(mock_code_repo),
        "AI_HISTORY_PATH": str(mock_ai_history_repo),
        "CLAUDE_API_KEY": "test-api-key",
        "CLAUDE_MODEL": "claude-3-5-sonnet-20241022",
        "POLL_INTERVAL": "2",
    }


@pytest.fixture
def git_repo(tmp_path) -> Path:
    """Create a temporary git repository for testing."""
    import subprocess

    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (repo_path / "README.md").write_text("# Test")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Rename branch to 'main' for consistency
    subprocess.run(
        ["git", "branch", "-M", "main"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def git_worktree(git_repo):
    """Create a git worktree for testing code application."""
    import subprocess

    worktree_path = git_repo / "worktrees" / "test-feature"

    # Create worktree with a new branch (using -b flag)
    subprocess.run(
        ["git", "worktree", "add", "-b", "feature/test-feature", str(worktree_path), "main"],
        cwd=git_repo,
        check=True,
        capture_output=True,
    )

    yield worktree_path

    # Cleanup
    subprocess.run(
        ["git", "worktree", "remove", str(worktree_path), "--force"],
        cwd=git_repo,
        check=False,
        capture_output=True,
    )
    # Also delete the branch
    subprocess.run(
        ["git", "branch", "-D", "feature/test-feature"],
        cwd=git_repo,
        check=False,
        capture_output=True,
    )


@pytest.fixture
def sample_markdown_with_patches():
    """Sample markdown with valid code patches."""
    return '''# Feature Implementation

Here's the implementation of the user authentication feature.

```typescript path=src/components/Button.tsx action=create
import React from 'react';

export const Button = ({ onClick }: { onClick: () => void }) => {
  return <button onClick={onClick}>Click Me</button>;
};
```

## API Updates

```python path=api/views.py action=update
from flask import jsonify

def get_data():
    """Return data from the API."""
    return jsonify({"status": "ok", "data": [1, 2, 3]})
```

## Cleanup

```typescript path=src/utils/legacy.ts action=delete
// This legacy utility file will be removed
export const oldFunction = () => console.log('deprecated');
```
'''


@pytest.fixture
def agent_output_structure(tmp_path):
    """Create complete agent output directory structure."""
    ai_history = tmp_path / "ai-history"
    feature_name = "test-feature"

    agents = ["00-meta", "01-architect", "02-openapi", "03-ui", "04-integration", "05-test"]

    structure = {}
    for agent in agents:
        agent_dir = ai_history / feature_name / agent
        for subdir in ["in", "out", "log"]:
            (agent_dir / subdir).mkdir(parents=True)
        structure[agent] = agent_dir

    return {"ai_history": ai_history, "feature_name": feature_name, "agents": structure}
