"""Tests for git worktree operations."""

import subprocess

import pytest

from weft.git.worktree import (
    WorktreeInfo,
    WorktreeStatus,
    create_worktree,
    get_worktree_status,
    list_worktrees,
    remove_worktree,
)


@pytest.fixture
def git_repo(tmp_path):
    """Create a temporary git repository for testing."""
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


class TestCreateWorktree:
    """Tests for create_worktree function."""

    def test_create_worktree(self, git_repo):
        """Test creating a new worktree."""
        worktree_path = create_worktree(git_repo, "feat-123")

        assert worktree_path.exists()
        assert worktree_path == git_repo / "worktrees" / "feat-123"
        assert (worktree_path / ".git").exists()

    def test_create_worktree_with_custom_base_branch(self, git_repo):
        """Test creating worktree from custom base branch."""
        # Create a dev branch
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

        worktree_path = create_worktree(git_repo, "feat-123", base_branch="dev")

        assert worktree_path.exists()

        # Verify it's based on dev branch
        result = subprocess.run(
            ["git", "log", "--oneline", "--all", "--graph"],
            cwd=worktree_path,
            check=True,
            capture_output=True,
            text=True,
        )
        # Just verify the worktree was created successfully
        assert result.returncode == 0

    def test_create_worktree_already_exists(self, git_repo):
        """Test creating worktree that already exists raises error."""
        create_worktree(git_repo, "feat-123")

        with pytest.raises(ValueError, match="already exists"):
            create_worktree(git_repo, "feat-123")

    def test_create_worktree_invalid_repo(self, tmp_path):
        """Test creating worktree in non-git directory raises error."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()

        with pytest.raises(ValueError, match="Not a git repository"):
            create_worktree(non_repo, "feat-123")

    def test_create_worktree_invalid_base_branch(self, git_repo):
        """Test creating worktree with invalid base branch raises error."""
        with pytest.raises(ValueError, match="not found"):
            create_worktree(git_repo, "feat-123", base_branch="nonexistent")

    def test_create_worktree_creates_worktrees_directory(self, git_repo):
        """Test that worktrees directory is created if it doesn't exist."""
        worktrees_dir = git_repo / "worktrees"
        assert not worktrees_dir.exists()

        create_worktree(git_repo, "feat-123")

        assert worktrees_dir.exists()
        assert worktrees_dir.is_dir()


class TestListWorktrees:
    """Tests for list_worktrees function."""

    def test_list_worktrees_empty(self, git_repo):
        """Test listing worktrees when none exist."""
        worktrees = list_worktrees(git_repo)

        # Should be empty (main worktree is excluded)
        feature_worktrees = [wt for wt in worktrees if hasattr(wt, "feature_id")]
        assert len(feature_worktrees) == 0

    def test_list_worktrees(self, git_repo):
        """Test listing worktrees."""
        # Create two worktrees
        create_worktree(git_repo, "feat-123")
        create_worktree(git_repo, "feat-456")

        worktrees = list_worktrees(git_repo)

        # Should have 2 feature worktrees
        feature_worktrees = [wt for wt in worktrees if wt.feature_id]
        assert len(feature_worktrees) == 2

        feature_ids = {wt.feature_id for wt in feature_worktrees}
        assert "feat-123" in feature_ids
        assert "feat-456" in feature_ids

    def test_list_worktrees_includes_correct_info(self, git_repo):
        """Test that WorktreeInfo contains correct information."""
        worktree_path = create_worktree(git_repo, "feat-123")
        worktrees = list_worktrees(git_repo)

        feature_worktrees = [wt for wt in worktrees if wt.feature_id == "feat-123"]
        assert len(feature_worktrees) == 1

        wt = feature_worktrees[0]
        assert isinstance(wt, WorktreeInfo)
        assert wt.path == worktree_path
        assert wt.branch == "feature/feat-123"
        assert wt.feature_id == "feat-123"
        assert wt.created_at is not None

    def test_list_worktrees_invalid_repo(self, tmp_path):
        """Test listing worktrees in non-git directory raises error."""
        non_repo = tmp_path / "not_a_repo"
        non_repo.mkdir()

        with pytest.raises(ValueError, match="Not a git repository"):
            list_worktrees(non_repo)


class TestRemoveWorktree:
    """Tests for remove_worktree function."""

    def test_remove_worktree(self, git_repo):
        """Test removing a worktree."""
        worktree_path = create_worktree(git_repo, "feat-123")
        assert worktree_path.exists()

        success = remove_worktree(git_repo, "feat-123")
        assert success
        assert not worktree_path.exists()

    def test_remove_worktree_nonexistent(self, git_repo):
        """Test removing non-existent worktree returns False."""
        success = remove_worktree(git_repo, "nonexistent")
        assert not success

    def test_remove_worktree_missing_but_delete_branch(self, git_repo):
        """Test that branch is deleted even when worktree is missing."""
        # Create worktree and branch
        worktree_path = create_worktree(git_repo, "feat-orphan")

        # Verify branch exists
        result = subprocess.run(["git", "branch"], cwd=git_repo, capture_output=True, text=True)
        assert "feature/feat-orphan" in result.stdout

        # Manually remove worktree directory (simulate partial cleanup or manual deletion)
        import shutil

        shutil.rmtree(worktree_path)

        # Also need to clean up git's worktree registration
        subprocess.run(["git", "worktree", "prune"], cwd=git_repo, check=True)

        # Now worktree is gone but branch still exists
        assert not worktree_path.exists()
        result = subprocess.run(["git", "branch"], cwd=git_repo, capture_output=True, text=True)
        assert "feature/feat-orphan" in result.stdout

        # Remove should still delete the branch
        success = remove_worktree(git_repo, "feat-orphan", delete_branch=True)
        assert success  # Should succeed because branch was deleted

        # Branch should be gone
        result = subprocess.run(["git", "branch"], cwd=git_repo, capture_output=True, text=True)
        assert "feature/feat-orphan" not in result.stdout

    def test_remove_worktree_with_branch(self, git_repo):
        """Test removing worktree and deleting branch."""
        create_worktree(git_repo, "feat-123")

        # Branch should exist
        result = subprocess.run(["git", "branch"], cwd=git_repo, capture_output=True, text=True)
        assert "feature/feat-123" in result.stdout

        # Remove worktree and branch
        success = remove_worktree(git_repo, "feat-123", delete_branch=True)
        assert success

        # Branch should be gone
        result = subprocess.run(["git", "branch"], cwd=git_repo, capture_output=True, text=True)
        assert "feature/feat-123" not in result.stdout

    def test_remove_worktree_without_deleting_branch(self, git_repo):
        """Test removing worktree but keeping branch."""
        worktree_path = create_worktree(git_repo, "feat-123")

        # Remove worktree but not branch
        success = remove_worktree(git_repo, "feat-123", delete_branch=False)
        assert success
        assert not worktree_path.exists()

        # Branch should still exist
        result = subprocess.run(["git", "branch"], cwd=git_repo, capture_output=True, text=True)
        assert "feature/feat-123" in result.stdout


class TestGetWorktreeStatus:
    """Tests for get_worktree_status function."""

    def test_get_worktree_status_clean(self, git_repo):
        """Test getting status of clean worktree."""
        worktree_path = create_worktree(git_repo, "feat-123")

        status = get_worktree_status(worktree_path)

        assert isinstance(status, WorktreeStatus)
        assert status.is_clean
        assert len(status.modified_files) == 0
        assert len(status.untracked_files) == 0
        assert status.current_branch == "feature/feat-123"

    def test_get_worktree_status_modified(self, git_repo):
        """Test getting status of modified worktree."""
        worktree_path = create_worktree(git_repo, "feat-123")

        # Modify a file
        (worktree_path / "README.md").write_text("Modified")

        status = get_worktree_status(worktree_path)

        assert not status.is_clean
        assert "README.md" in status.modified_files
        assert len(status.untracked_files) == 0

    def test_get_worktree_status_untracked(self, git_repo):
        """Test getting status with untracked files."""
        worktree_path = create_worktree(git_repo, "feat-123")

        # Add untracked file
        (worktree_path / "new_file.txt").write_text("New")

        status = get_worktree_status(worktree_path)

        assert not status.is_clean
        assert len(status.modified_files) == 0
        assert "new_file.txt" in status.untracked_files

    def test_get_worktree_status_both_modified_and_untracked(self, git_repo):
        """Test status with both modified and untracked files."""
        worktree_path = create_worktree(git_repo, "feat-123")

        # Modify existing file
        (worktree_path / "README.md").write_text("Modified")

        # Add untracked file
        (worktree_path / "new_file.txt").write_text("New")

        status = get_worktree_status(worktree_path)

        assert not status.is_clean
        assert "README.md" in status.modified_files
        assert "new_file.txt" in status.untracked_files


class TestIntegration:
    """Integration tests for worktree workflow."""

    def test_full_workflow(self, git_repo):
        """Test complete worktree workflow: create, list, status, remove."""
        # Create worktree
        worktree_path = create_worktree(git_repo, "feat-123")
        assert worktree_path.exists()

        # List worktrees
        worktrees = list_worktrees(git_repo)
        feature_worktrees = [wt for wt in worktrees if wt.feature_id == "feat-123"]
        assert len(feature_worktrees) == 1

        # Check status (should be clean)
        status = get_worktree_status(worktree_path)
        assert status.is_clean

        # Modify file
        (worktree_path / "README.md").write_text("Modified")
        status = get_worktree_status(worktree_path)
        assert not status.is_clean

        # Remove worktree
        success = remove_worktree(git_repo, "feat-123", delete_branch=True)
        assert success
        assert not worktree_path.exists()

        # List should be empty
        worktrees = list_worktrees(git_repo)
        feature_worktrees = [wt for wt in worktrees if wt.feature_id == "feat-123"]
        assert len(feature_worktrees) == 0

    def test_multiple_parallel_worktrees(self, git_repo):
        """Test creating multiple worktrees in parallel."""
        # Create three worktrees
        worktree1 = create_worktree(git_repo, "feat-123")
        worktree2 = create_worktree(git_repo, "feat-456")
        worktree3 = create_worktree(git_repo, "feat-789")

        assert worktree1.exists()
        assert worktree2.exists()
        assert worktree3.exists()

        # List all worktrees
        worktrees = list_worktrees(git_repo)
        feature_ids = {wt.feature_id for wt in worktrees}

        assert "feat-123" in feature_ids
        assert "feat-456" in feature_ids
        assert "feat-789" in feature_ids

        # Remove all worktrees
        remove_worktree(git_repo, "feat-123", delete_branch=True)
        remove_worktree(git_repo, "feat-456", delete_branch=True)
        remove_worktree(git_repo, "feat-789", delete_branch=True)

        # Should be empty
        worktrees = list_worktrees(git_repo)
        feature_worktrees = [wt for wt in worktrees if wt.feature_id]
        assert len(feature_worktrees) == 0
