"""Tests for feature initialization CLI."""

import subprocess

import pytest

from weft.cli.feature.helpers import initialize_feature, validate_feature_id


class TestValidateFeatureId:
    """Tests for validate_feature_id function."""

    def test_validate_feature_id_valid(self):
        """Test valid feature IDs pass validation."""
        assert validate_feature_id("feat-123")
        assert validate_feature_id("feature_456")
        assert validate_feature_id("abc-123-xyz")
        assert validate_feature_id("feature")
        assert validate_feature_id("f123")

    def test_validate_feature_id_empty(self):
        """Test empty feature ID raises error."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_feature_id("")

    def test_validate_feature_id_too_short(self):
        """Test too short feature ID raises error."""
        with pytest.raises(ValueError, match="must be 3-50 characters"):
            validate_feature_id("ab")

    def test_validate_feature_id_too_long(self):
        """Test too long feature ID raises error."""
        long_id = "a" * 51
        with pytest.raises(ValueError, match="must be 3-50 characters"):
            validate_feature_id(long_id)

    def test_validate_feature_id_starts_with_number(self):
        """Test feature ID starting with number raises error."""
        with pytest.raises(ValueError, match="must start with a letter"):
            validate_feature_id("123-feat")

    def test_validate_feature_id_invalid_characters(self):
        """Test feature ID with invalid characters raises error."""
        with pytest.raises(ValueError, match="can only contain"):
            validate_feature_id("feat@123")

        with pytest.raises(ValueError, match="can only contain"):
            validate_feature_id("feat.123")

        with pytest.raises(ValueError, match="can only contain"):
            validate_feature_id("feat 123")


@pytest.fixture
def history_repo(tmp_path):
    """Create a temporary AI history repository."""
    history_path = tmp_path / "history"
    history_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=history_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=history_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=history_path,
        check=True,
        capture_output=True,
    )

    # Create initial commit
    (history_path / "README.md").write_text("# AI History")
    subprocess.run(["git", "add", "README.md"], cwd=history_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=history_path,
        check=True,
        capture_output=True,
    )

    return history_path


class TestInitializeFeature:
    """Tests for initialize_feature function."""

    def test_initialize_feature_default_agents(self, git_repo, history_repo):
        """Test feature initialization with default agents."""
        result = initialize_feature(
            feature_id="feat-123",
            code_repo_path=git_repo,
            ai_history_path=history_repo,
        )

        assert result["feature_id"] == "feat-123"
        assert result["worktree_path"].exists()
        assert result["status"] == "initialized"
        assert result["base_branch"] == "main"

        # Check default agents created
        assert len(result["agents"]) == 6
        assert "00-meta" in result["agents"]
        assert "01-architect" in result["agents"]

        # Verify history structure
        feature_path = history_repo / "feat-123"
        assert feature_path.exists()
        assert (feature_path / "00-meta" / "in").exists()
        assert (feature_path / "01-architect" / "in").exists()

    def test_initialize_feature_custom_agents(self, git_repo, history_repo):
        """Test feature initialization with custom agents."""
        result = initialize_feature(
            feature_id="feat-123",
            code_repo_path=git_repo,
            ai_history_path=history_repo,
            agents=["00-meta", "01-architect"],
        )

        assert result["feature_id"] == "feat-123"
        assert result["worktree_path"].exists()
        assert len(result["agents"]) == 2
        assert "00-meta" in result["agents"]
        assert "01-architect" in result["agents"]

        # Verify only requested agents created
        feature_path = history_repo / "feat-123"
        assert (feature_path / "00-meta" / "in").exists()
        assert (feature_path / "01-architect" / "in").exists()
        assert not (feature_path / "02-openapi" / "in").exists()

    def test_initialize_feature_custom_base_branch(self, git_repo, history_repo):
        """Test feature initialization with custom base branch."""
        # Create dev branch
        subprocess.run(
            ["git", "checkout", "-b", "dev"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "checkout", "main"],
            cwd=git_repo,
            check=True,
            capture_output=True,
        )

        result = initialize_feature(
            feature_id="feat-123",
            code_repo_path=git_repo,
            ai_history_path=history_repo,
            base_branch="dev",
            agents=["00-meta"],
        )

        assert result["base_branch"] == "dev"
        assert result["worktree_path"].exists()

    def test_initialize_feature_invalid_id(self, git_repo, history_repo):
        """Test initialization with invalid feature ID raises error."""
        with pytest.raises(ValueError, match="must start with a letter"):
            initialize_feature(
                feature_id="123-invalid",
                code_repo_path=git_repo,
                ai_history_path=history_repo,
            )

    def test_initialize_feature_already_exists(self, git_repo, history_repo):
        """Test initialization of existing feature raises error."""
        # Create feature once
        initialize_feature(
            feature_id="feat-123",
            code_repo_path=git_repo,
            ai_history_path=history_repo,
            agents=["00-meta"],
        )

        # Try to create again
        with pytest.raises(ValueError, match="already exists"):
            initialize_feature(
                feature_id="feat-123",
                code_repo_path=git_repo,
                ai_history_path=history_repo,
                agents=["00-meta"],
            )

    def test_initialize_feature_invalid_base_branch(self, git_repo, history_repo):
        """Test initialization with invalid base branch raises error."""
        with pytest.raises(ValueError, match="not found"):
            initialize_feature(
                feature_id="feat-123",
                code_repo_path=git_repo,
                ai_history_path=history_repo,
                base_branch="nonexistent",
                agents=["00-meta"],
            )

    def test_initialize_feature_rollback_on_history_failure(self, git_repo, history_repo):
        """Test that worktree is rolled back if history creation fails."""
        # Create a non-git directory to cause history creation to fail
        non_git_history = history_repo.parent / "non_git"
        non_git_history.mkdir()

        with pytest.raises(ValueError, match="Invalid AI history repository"):
            initialize_feature(
                feature_id="feat-123",
                code_repo_path=git_repo,
                ai_history_path=non_git_history,
                agents=["00-meta"],
            )

        # Verify worktree was rolled back
        worktree_path = git_repo / "worktrees" / "feat-123"
        assert not worktree_path.exists()
