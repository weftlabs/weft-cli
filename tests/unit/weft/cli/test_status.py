"""Tests for status CLI command."""

import pytest
from click.testing import CliRunner

from weft.cli.status import get_feature_status, status_command
from weft.config.settings import Settings


class TestGetFeatureStatus:
    """Tests for get_feature_status function."""

    def test_get_feature_status(self, tmp_path):
        """Test getting feature status."""
        # Setup
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"

        # Create agent directories with files
        (feature_path / "00-meta" / "in").mkdir(parents=True)
        (feature_path / "00-meta" / "out").mkdir(parents=True)
        (feature_path / "01-architect" / "in").mkdir(parents=True)
        (feature_path / "01-architect" / "out").mkdir(parents=True)

        # Add some files
        (feature_path / "00-meta" / "in" / "prompt-001.md").write_text("prompt 1")
        (feature_path / "00-meta" / "out" / "result-001.md").write_text("result 1")
        (feature_path / "01-architect" / "in" / "prompt-001.md").write_text("prompt 2")

        # Get status (without worktree for simplicity)
        status = get_feature_status(
            code_repo_path=tmp_path,
            ai_history_path=history_path,
            feature_id="feat-123",
        )

        assert status["feature_id"] == "feat-123"
        assert status["feature_path"] == feature_path
        assert len(status["agents"]) == 2

        # Check 00-meta
        meta_agent = next(a for a in status["agents"] if a["agent_id"] == "00-meta")
        assert meta_agent["pending_count"] == 1
        assert meta_agent["completed_count"] == 1
        assert meta_agent["last_activity"] is not None

        # Check 01-architect
        architect_agent = next(a for a in status["agents"] if a["agent_id"] == "01-architect")
        assert architect_agent["pending_count"] == 1
        assert architect_agent["completed_count"] == 0

    def test_get_feature_status_empty_feature(self, tmp_path):
        """Test getting status for feature with no tasks."""
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"

        # Create agent directories but no files
        (feature_path / "00-meta" / "in").mkdir(parents=True)
        (feature_path / "00-meta" / "out").mkdir(parents=True)

        status = get_feature_status(
            code_repo_path=tmp_path,
            ai_history_path=history_path,
            feature_id="feat-123",
        )

        assert status["feature_id"] == "feat-123"
        assert len(status["agents"]) == 1

        meta_agent = status["agents"][0]
        assert meta_agent["pending_count"] == 0
        assert meta_agent["completed_count"] == 0
        assert meta_agent["last_activity"] is None

    def test_get_feature_status_not_found(self, tmp_path):
        """Test status for non-existent feature raises error."""
        history_path = tmp_path / "history"
        history_path.mkdir()

        with pytest.raises(ValueError, match="Feature does not exist"):
            get_feature_status(
                code_repo_path=tmp_path,
                ai_history_path=history_path,
                feature_id="feat-999",
            )

    def test_get_feature_status_with_worktree(self, git_repo, tmp_path):
        """Test status includes worktree information."""
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"
        (feature_path / "00-meta" / "in").mkdir(parents=True)

        # Create a worktree
        from weft.git.worktree import create_worktree

        worktree_path = create_worktree(git_repo, "feat-123")

        status = get_feature_status(
            code_repo_path=git_repo,
            ai_history_path=history_path,
            feature_id="feat-123",
        )

        assert status["worktree"] is not None
        assert status["worktree"]["path"] == worktree_path
        assert status["worktree"]["branch"] == "feature/feat-123"
        assert status["worktree"]["is_clean"] is True

    def test_get_feature_status_multiple_agents(self, tmp_path):
        """Test status with multiple agents."""
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"

        # Create multiple agent directories
        for agent_id in ["00-meta", "01-architect", "02-openapi"]:
            (feature_path / agent_id / "in").mkdir(parents=True)
            (feature_path / agent_id / "out").mkdir(parents=True)
            # Add files to each
            (feature_path / agent_id / "in" / "prompt-001.md").write_text("test")

        status = get_feature_status(
            code_repo_path=tmp_path,
            ai_history_path=history_path,
            feature_id="feat-123",
        )

        assert len(status["agents"]) == 3
        agent_ids = {a["agent_id"] for a in status["agents"]}
        assert agent_ids == {"00-meta", "01-architect", "02-openapi"}


class TestStatusCommand:
    """Tests for status CLI command."""

    def test_status_command_basic(self, tmp_path, monkeypatch):
        """Test status command displays feature status."""
        # Setup
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"
        (feature_path / "00-meta" / "in").mkdir(parents=True)
        (feature_path / "00-meta" / "out").mkdir(parents=True)
        (feature_path / "00-meta" / "in" / "prompt-001.md").write_text("test")

        # Mock settings
        mock_settings = Settings(
            code_repo_path=tmp_path,
            ai_history_path=history_path,
            anthropic_api_key="test-key",
            model="claude-3-opus",
            poll_interval=2,
        )

        monkeypatch.setattr("weft.cli.status.get_settings", lambda: mock_settings)

        runner = CliRunner()
        result = runner.invoke(status_command, ["feat-123"])

        assert result.exit_code == 0
        assert "Feature: feat-123" in result.output
        assert "00-meta" in result.output
        assert "Agents:" in result.output

    def test_status_command_specific_agent(self, tmp_path, monkeypatch):
        """Test status command for specific agent."""
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"
        (feature_path / "00-meta" / "in").mkdir(parents=True)
        (feature_path / "01-architect" / "in").mkdir(parents=True)

        mock_settings = Settings(
            code_repo_path=tmp_path,
            ai_history_path=history_path,
            anthropic_api_key="test-key",
            model="claude-3-opus",
            poll_interval=2,
        )

        monkeypatch.setattr("weft.cli.status.get_settings", lambda: mock_settings)

        runner = CliRunner()
        result = runner.invoke(status_command, ["feat-123", "--agent", "00-meta"])

        assert result.exit_code == 0
        assert "00-meta" in result.output
        # Should not show 01-architect
        assert "01-architect" not in result.output

    def test_status_command_verbose(self, tmp_path, monkeypatch):
        """Test status command with verbose flag."""
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"
        (feature_path / "00-meta" / "in").mkdir(parents=True)
        (feature_path / "00-meta" / "in" / "prompt-001.md").write_text("test")

        mock_settings = Settings(
            code_repo_path=tmp_path,
            ai_history_path=history_path,
            anthropic_api_key="test-key",
            model="claude-3-opus",
            poll_interval=2,
        )

        monkeypatch.setattr("weft.cli.status.get_settings", lambda: mock_settings)

        runner = CliRunner()
        result = runner.invoke(status_command, ["feat-123", "--verbose"])

        assert result.exit_code == 0
        assert "prompt-001.md" in result.output
        assert "Pending:" in result.output

    def test_status_command_feature_not_found(self, tmp_path, monkeypatch):
        """Test status command with non-existent feature."""
        history_path = tmp_path / "history"
        history_path.mkdir()

        mock_settings = Settings(
            code_repo_path=tmp_path,
            ai_history_path=history_path,
            anthropic_api_key="test-key",
            model="claude-3-opus",
            poll_interval=2,
        )

        monkeypatch.setattr("weft.cli.status.get_settings", lambda: mock_settings)

        runner = CliRunner()
        result = runner.invoke(status_command, ["feat-999"])

        assert result.exit_code == 1
        assert "Feature does not exist" in result.output

    def test_status_command_invalid_agent(self, tmp_path, monkeypatch):
        """Test status command with invalid agent filter."""
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"
        (feature_path / "00-meta" / "in").mkdir(parents=True)

        mock_settings = Settings(
            code_repo_path=tmp_path,
            ai_history_path=history_path,
            anthropic_api_key="test-key",
            model="claude-3-opus",
            poll_interval=2,
        )

        monkeypatch.setattr("weft.cli.status.get_settings", lambda: mock_settings)

        runner = CliRunner()
        result = runner.invoke(status_command, ["feat-123", "--agent", "99-invalid"])

        assert result.exit_code == 1
        assert "Agent not found" in result.output

    def test_status_command_with_worktree(self, git_repo, tmp_path, monkeypatch):
        """Test status command shows worktree information."""
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"
        (feature_path / "00-meta" / "in").mkdir(parents=True)

        # Create a worktree
        from weft.git.worktree import create_worktree

        create_worktree(git_repo, "feat-123")

        mock_settings = Settings(
            code_repo_path=git_repo,
            ai_history_path=history_path,
            anthropic_api_key="test-key",
            model="claude-3-opus",
            poll_interval=2,
        )

        monkeypatch.setattr("weft.cli.status.get_settings", lambda: mock_settings)

        runner = CliRunner()
        result = runner.invoke(status_command, ["feat-123"])

        assert result.exit_code == 0
        assert "Worktree:" in result.output
        assert "feature/feat-123" in result.output
        assert "Clean" in result.output

    def test_status_command_dirty_worktree_verbose(self, git_repo, tmp_path, monkeypatch):
        """Test status shows modified files in verbose mode."""
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"
        (feature_path / "00-meta" / "in").mkdir(parents=True)

        # Create worktree and modify file
        from weft.git.worktree import create_worktree

        worktree_path = create_worktree(git_repo, "feat-123")
        (worktree_path / "README.md").write_text("Modified")

        mock_settings = Settings(
            code_repo_path=git_repo,
            ai_history_path=history_path,
            anthropic_api_key="test-key",
            model="claude-3-opus",
            poll_interval=2,
        )

        monkeypatch.setattr("weft.cli.status.get_settings", lambda: mock_settings)

        runner = CliRunner()
        result = runner.invoke(status_command, ["feat-123", "--verbose"])

        assert result.exit_code == 0
        assert "Dirty" in result.output
        assert "README.md" in result.output

    def test_status_command_summary_counts(self, tmp_path, monkeypatch):
        """Test status command shows summary counts."""
        history_path = tmp_path / "history"
        feature_path = history_path / "feat-123"

        # Create multiple agents with different counts
        (feature_path / "00-meta" / "in").mkdir(parents=True)
        (feature_path / "00-meta" / "out").mkdir(parents=True)
        (feature_path / "01-architect" / "in").mkdir(parents=True)
        (feature_path / "01-architect" / "out").mkdir(parents=True)

        # Add files
        (feature_path / "00-meta" / "in" / "prompt-001.md").write_text("test")
        (feature_path / "00-meta" / "out" / "result-001.md").write_text("test")
        (feature_path / "01-architect" / "in" / "prompt-001.md").write_text("test")
        (feature_path / "01-architect" / "in" / "prompt-002.md").write_text("test")

        mock_settings = Settings(
            code_repo_path=tmp_path,
            ai_history_path=history_path,
            anthropic_api_key="test-key",
            model="claude-3-opus",
            poll_interval=2,
        )

        monkeypatch.setattr("weft.cli.status.get_settings", lambda: mock_settings)

        runner = CliRunner()
        result = runner.invoke(status_command, ["feat-123"])

        assert result.exit_code == 0
        assert "Total: 3 pending, 1 completed" in result.output
