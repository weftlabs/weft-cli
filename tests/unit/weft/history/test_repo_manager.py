"""Tests for AI History Repository Manager."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from weft.history.repo_manager import (
    create_feature_structure,
    get_feature_agents,
    initialize_ai_history_repo,
    validate_ai_history_repo,
)


class TestInitializeAiHistoryRepo:
    """Tests for initialize_ai_history_repo function."""

    def test_initialize_new_repo_success(self, temp_dir: Path) -> None:
        """Test successful initialization of a new repository."""
        repo_path = temp_dir / "new-repo"

        result = initialize_ai_history_repo(repo_path)

        assert result is True
        assert repo_path.exists()
        assert (repo_path / ".git").exists()

    def test_initialize_existing_directory(self, temp_dir: Path) -> None:
        """Test initialization in an existing directory."""
        repo_path = temp_dir / "existing-dir"
        repo_path.mkdir()

        result = initialize_ai_history_repo(repo_path)

        assert result is True
        assert (repo_path / ".git").exists()

    def test_initialize_nested_path(self, temp_dir: Path) -> None:
        """Test initialization with nested directory path."""
        repo_path = temp_dir / "level1" / "level2" / "repo"

        result = initialize_ai_history_repo(repo_path)

        assert result is True
        assert repo_path.exists()
        assert (repo_path / ".git").exists()

    def test_initialize_already_git_repo(self, temp_dir: Path) -> None:
        """Test initialization of an existing git repository."""
        repo_path = temp_dir / "existing-repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True, check=True)

        result = initialize_ai_history_repo(repo_path)

        # Should succeed even if already a git repo
        assert result is True
        assert (repo_path / ".git").exists()

    @patch("subprocess.run")
    def test_initialize_git_command_fails(self, mock_run: MagicMock, temp_dir: Path) -> None:
        """Test handling when git init command fails."""
        repo_path = temp_dir / "fail-repo"

        # Mock git init to fail
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        result = initialize_ai_history_repo(repo_path)

        assert result is False

    @patch("pathlib.Path.mkdir")
    def test_initialize_directory_creation_fails(
        self, mock_mkdir: MagicMock, temp_dir: Path
    ) -> None:
        """Test handling when directory creation fails."""
        repo_path = temp_dir / "fail-dir"

        # Mock mkdir to raise OSError
        mock_mkdir.side_effect = OSError("Permission denied")

        result = initialize_ai_history_repo(repo_path)

        assert result is False


class TestValidateAiHistoryRepo:
    """Tests for validate_ai_history_repo function."""

    def test_validate_valid_repo(self, mock_ai_history_repo: Path) -> None:
        """Test validation of a valid AI history repository."""
        result = validate_ai_history_repo(mock_ai_history_repo)

        assert result is True

    def test_validate_nonexistent_path(self, temp_dir: Path) -> None:
        """Test validation of a non-existent path."""
        repo_path = temp_dir / "does-not-exist"

        result = validate_ai_history_repo(repo_path)

        assert result is False

    def test_validate_file_instead_of_directory(self, temp_dir: Path) -> None:
        """Test validation when path is a file instead of directory."""
        file_path = temp_dir / "file.txt"
        file_path.touch()

        result = validate_ai_history_repo(file_path)

        assert result is False

    def test_validate_directory_without_git(self, temp_dir: Path) -> None:
        """Test validation of directory without .git."""
        repo_path = temp_dir / "not-a-repo"
        repo_path.mkdir()

        result = validate_ai_history_repo(repo_path)

        assert result is False

    def test_validate_corrupted_git_repo(self, temp_dir: Path) -> None:
        """Test validation of a corrupted git repository."""
        repo_path = temp_dir / "corrupted-repo"
        repo_path.mkdir()
        # Create .git directory but don't initialize properly
        (repo_path / ".git").mkdir()

        result = validate_ai_history_repo(repo_path)

        # Should fail because git rev-parse will fail
        assert result is False

    @patch("subprocess.run")
    def test_validate_subprocess_error(
        self, mock_run: MagicMock, mock_ai_history_repo: Path
    ) -> None:
        """Test handling when subprocess raises an error."""
        mock_run.side_effect = subprocess.SubprocessError("Git command failed")

        result = validate_ai_history_repo(mock_ai_history_repo)

        assert result is False


class TestCreateFeatureStructure:
    """Tests for create_feature_structure function."""

    def test_create_feature_structure_success(self, mock_ai_history_repo: Path) -> None:
        """Test successful creation of feature structure."""
        feature_id = "FEAT-123"
        agents = ["01-architect", "02-openapi"]

        create_feature_structure(mock_ai_history_repo, feature_id, agents)

        # Verify feature directory created
        feature_path = mock_ai_history_repo / feature_id
        assert feature_path.exists()

        # Verify agent directories created with subdirectories
        for agent_id in agents:
            agent_path = feature_path / agent_id
            assert agent_path.exists()
            assert (agent_path / "in").exists()
            assert (agent_path / "out").exists()
            assert (agent_path / "log").exists()

    def test_create_feature_structure_multiple_agents(self, mock_ai_history_repo: Path) -> None:
        """Test creation with multiple agents."""
        feature_id = "FEAT-456"
        agents = [
            "01-architect",
            "02-openapi",
            "03-ui-skeleton",
            "04-integration",
            "05-test-review",
        ]

        create_feature_structure(mock_ai_history_repo, feature_id, agents)

        feature_path = mock_ai_history_repo / feature_id
        for agent_id in agents:
            agent_path = feature_path / agent_id
            assert agent_path.exists()
            assert (agent_path / "in").is_dir()
            assert (agent_path / "out").is_dir()
            assert (agent_path / "log").is_dir()

    def test_create_feature_structure_existing_feature(self, mock_ai_history_repo: Path) -> None:
        """Test creation when feature directory already exists."""
        feature_id = "FEAT-789"
        agents = ["01-architect"]

        # Create feature once
        create_feature_structure(mock_ai_history_repo, feature_id, agents)

        # Create again with additional agent
        agents_extended = ["01-architect", "02-openapi"]
        create_feature_structure(mock_ai_history_repo, feature_id, agents_extended)

        # Both agents should exist
        feature_path = mock_ai_history_repo / feature_id
        for agent_id in agents_extended:
            assert (feature_path / agent_id / "in").exists()

    def test_create_feature_structure_empty_agents_list(self, mock_ai_history_repo: Path) -> None:
        """Test creation with empty agents list."""
        feature_id = "FEAT-EMPTY"
        agents = []

        create_feature_structure(mock_ai_history_repo, feature_id, agents)

        # Feature directory should be created even with no agents
        feature_path = mock_ai_history_repo / feature_id
        assert feature_path.exists()

    def test_create_feature_structure_invalid_repo(self, temp_dir: Path) -> None:
        """Test creation fails with invalid repository."""
        invalid_repo = temp_dir / "not-a-repo"
        invalid_repo.mkdir()

        feature_id = "FEAT-FAIL"
        agents = ["01-architect"]

        with pytest.raises(ValueError, match="Invalid AI history repository"):
            create_feature_structure(invalid_repo, feature_id, agents)

    def test_create_feature_structure_nonexistent_repo(self, temp_dir: Path) -> None:
        """Test creation fails with non-existent repository."""
        nonexistent_repo = temp_dir / "does-not-exist"

        feature_id = "FEAT-FAIL"
        agents = ["01-architect"]

        with pytest.raises(ValueError, match="Invalid AI history repository"):
            create_feature_structure(nonexistent_repo, feature_id, agents)

    @patch("pathlib.Path.mkdir")
    def test_create_feature_structure_mkdir_fails(
        self, mock_mkdir: MagicMock, mock_ai_history_repo: Path
    ) -> None:
        """Test handling when directory creation fails."""
        feature_id = "FEAT-FAIL"
        agents = ["01-architect"]

        # Mock mkdir to raise OSError
        mock_mkdir.side_effect = OSError("Permission denied")

        with pytest.raises(OSError):
            create_feature_structure(mock_ai_history_repo, feature_id, agents)


class TestGetFeatureAgents:
    """Tests for get_feature_agents function."""

    def test_get_feature_agents_success(self, mock_ai_history_repo: Path) -> None:
        """Test getting agents from a feature."""
        feature_id = "FEAT-GET-1"
        agents = ["01-architect", "02-openapi", "03-ui-skeleton"]

        # Create feature structure
        create_feature_structure(mock_ai_history_repo, feature_id, agents)

        # Get agents
        result = get_feature_agents(mock_ai_history_repo, feature_id)

        assert result == agents  # Should be sorted

    def test_get_feature_agents_sorted(self, mock_ai_history_repo: Path) -> None:
        """Test that agents are returned in sorted order."""
        feature_id = "FEAT-GET-2"
        agents = ["03-ui-skeleton", "01-architect", "02-openapi"]  # Unsorted

        create_feature_structure(mock_ai_history_repo, feature_id, agents)

        result = get_feature_agents(mock_ai_history_repo, feature_id)

        assert result == sorted(agents)

    def test_get_feature_agents_empty_feature(self, mock_ai_history_repo: Path) -> None:
        """Test getting agents from feature with no agents."""
        feature_id = "FEAT-EMPTY"
        feature_path = mock_ai_history_repo / feature_id
        feature_path.mkdir()

        result = get_feature_agents(mock_ai_history_repo, feature_id)

        assert result == []

    def test_get_feature_agents_partial_structure(self, mock_ai_history_repo: Path) -> None:
        """Test getting agents when some directories are incomplete."""
        feature_id = "FEAT-PARTIAL"
        feature_path = mock_ai_history_repo / feature_id
        feature_path.mkdir()

        # Create complete agent structure
        complete_agent = feature_path / "01-architect"
        (complete_agent / "in").mkdir(parents=True)
        (complete_agent / "out").mkdir(parents=True)
        (complete_agent / "log").mkdir(parents=True)

        # Create incomplete agent structure (missing log/)
        incomplete_agent = feature_path / "02-openapi"
        (incomplete_agent / "in").mkdir(parents=True)
        (incomplete_agent / "out").mkdir(parents=True)

        # Create random directory
        (feature_path / "random-dir").mkdir()

        result = get_feature_agents(mock_ai_history_repo, feature_id)

        # Should only return complete agent
        assert result == ["01-architect"]

    def test_get_feature_agents_nonexistent_feature(self, mock_ai_history_repo: Path) -> None:
        """Test getting agents from non-existent feature."""
        feature_id = "FEAT-DOES-NOT-EXIST"

        with pytest.raises(FileNotFoundError, match="Feature directory not found"):
            get_feature_agents(mock_ai_history_repo, feature_id)

    def test_get_feature_agents_invalid_repo(self, temp_dir: Path) -> None:
        """Test getting agents from invalid repository."""
        invalid_repo = temp_dir / "not-a-repo"
        invalid_repo.mkdir()

        with pytest.raises(ValueError, match="Invalid AI history repository"):
            get_feature_agents(invalid_repo, "FEAT-123")

    def test_get_feature_agents_with_files(self, mock_ai_history_repo: Path) -> None:
        """Test that files in feature directory are ignored."""
        feature_id = "FEAT-WITH-FILES"
        agents = ["01-architect"]

        create_feature_structure(mock_ai_history_repo, feature_id, agents)

        # Add some files to feature directory
        feature_path = mock_ai_history_repo / feature_id
        (feature_path / "README.md").touch()
        (feature_path / "notes.txt").touch()

        result = get_feature_agents(mock_ai_history_repo, feature_id)

        # Should only return agent directories
        assert result == ["01-architect"]
