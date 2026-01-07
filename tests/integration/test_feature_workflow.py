"""Integration tests for complete feature workflows.

These tests verify end-to-end workflows from feature initialization
through agent processing.
"""

import subprocess

import pytest

from weft.cli.feature.helpers import initialize_feature
from weft.git.worktree import get_worktree_status, list_worktrees
from weft.queue.file_ops import list_pending_prompts, write_prompt
from weft.queue.models import PromptTask


@pytest.fixture
def test_git_repo(tmp_path):
    """Create a test git repository."""
    repo_path = tmp_path / "code_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
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
    (repo_path / "README.md").write_text("# Test Repo")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "branch", "-M", "main"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def test_ai_history_repo(tmp_path):
    """Create a test AI history repository."""
    history_path = tmp_path / "ai_history"
    history_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=history_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
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


class TestFeatureLifecycle:
    """Tests for complete feature lifecycle."""

    def test_complete_feature_workflow(self, test_git_repo, test_ai_history_repo):
        """Test complete feature workflow from init to submission."""
        feature_id = "feat-workflow-001"

        # Step 1: Initialize feature
        result = initialize_feature(
            feature_id=feature_id,
            code_repo_path=test_git_repo,
            ai_history_path=test_ai_history_repo,
            agents=["00-meta", "01-architect"],
        )

        assert result["feature_id"] == feature_id
        assert result["status"] == "initialized"
        assert result["worktree_path"].exists()

        # Step 2: Verify worktree created
        worktrees = list_worktrees(test_git_repo)
        feature_worktrees = [wt for wt in worktrees if wt.feature_id == feature_id]
        assert len(feature_worktrees) == 1
        assert feature_worktrees[0].branch == f"feature/{feature_id}"

        # Step 3: Submit prompt to agent
        prompt_task = PromptTask(
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_text="Add user authentication with JWT tokens",
            spec_version="1.0.0",
            revision=1,
        )

        prompt_file = write_prompt(
            ai_history_path=test_ai_history_repo,
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_task=prompt_task,
        )

        assert prompt_file.exists()
        assert prompt_file.suffix == ".md"

        # Step 4: Verify prompt is in queue
        agent_dir = test_ai_history_repo / feature_id / "00-meta"
        pending = list_pending_prompts(agent_dir)

        assert len(pending) == 1
        assert pending[0].name == prompt_file.name

        # Step 5: Verify directory structure
        feature_path = test_ai_history_repo / feature_id
        assert (feature_path / "00-meta" / "in").exists()
        assert (feature_path / "00-meta" / "out").exists()
        assert (feature_path / "01-architect" / "in").exists()
        assert (feature_path / "01-architect" / "out").exists()

    def test_multi_agent_workflow(self, test_git_repo, test_ai_history_repo):
        """Test workflow with multiple agents in sequence."""
        feature_id = "feat-multi-001"

        # Initialize
        initialize_feature(
            feature_id=feature_id,
            code_repo_path=test_git_repo,
            ai_history_path=test_ai_history_repo,
            agents=["00-meta", "01-architect"],
        )

        # Submit to Agent 00
        task_00 = PromptTask(
            feature_id=feature_id,
            agent_id="00-meta",
            prompt_text="Feature request for payment processing",
            spec_version="1.0.0",
        )
        write_prompt(test_ai_history_repo, feature_id, "00-meta", task_00)

        # Submit to Agent 01
        task_01 = PromptTask(
            feature_id=feature_id,
            agent_id="01-architect",
            prompt_text="Design payment architecture with Stripe",
            spec_version="1.0.0",
        )
        write_prompt(test_ai_history_repo, feature_id, "01-architect", task_01)

        # Verify both agents have pending tasks
        agent_dir_00 = test_ai_history_repo / feature_id / "00-meta"
        agent_dir_01 = test_ai_history_repo / feature_id / "01-architect"
        pending_00 = list_pending_prompts(agent_dir_00)
        pending_01 = list_pending_prompts(agent_dir_01)

        assert len(pending_00) == 1
        assert len(pending_01) == 1

    def test_worktree_integration(self, test_git_repo, test_ai_history_repo):
        """Test worktree integration with feature workflow."""
        feature_id = "feat-worktree-001"

        # Initialize feature (creates worktree)
        result = initialize_feature(
            feature_id=feature_id,
            code_repo_path=test_git_repo,
            ai_history_path=test_ai_history_repo,
            agents=["00-meta"],
        )

        worktree_path = result["worktree_path"]

        # Verify worktree is clean initially
        status = get_worktree_status(worktree_path)
        assert status.is_clean
        assert status.current_branch == f"feature/{feature_id}"

        # Make a change in worktree
        (worktree_path / "test.txt").write_text("Test file")

        # Verify worktree shows untracked file
        status = get_worktree_status(worktree_path)
        assert not status.is_clean
        assert "test.txt" in status.untracked_files

    def test_multiple_features_parallel(self, test_git_repo, test_ai_history_repo):
        """Test multiple features can be worked on in parallel."""
        feature_ids = ["feat-parallel-001", "feat-parallel-002", "feat-parallel-003"]

        # Initialize multiple features
        for feature_id in feature_ids:
            initialize_feature(
                feature_id=feature_id,
                code_repo_path=test_git_repo,
                ai_history_path=test_ai_history_repo,
                agents=["00-meta"],
            )

        # Verify all worktrees exist
        worktrees = list_worktrees(test_git_repo)
        feature_worktrees = [wt for wt in worktrees if wt.feature_id in feature_ids]
        assert len(feature_worktrees) == 3

        # Verify all have AI history structure
        for feature_id in feature_ids:
            feature_path = test_ai_history_repo / feature_id
            assert feature_path.exists()
            assert (feature_path / "00-meta" / "in").exists()

    def test_feature_with_custom_agents(self, test_git_repo, test_ai_history_repo):
        """Test feature initialization with custom agent selection."""
        feature_id = "feat-custom-agents"

        # Initialize with only specific agents
        result = initialize_feature(
            feature_id=feature_id,
            code_repo_path=test_git_repo,
            ai_history_path=test_ai_history_repo,
            agents=["00-meta", "01-architect", "05-test"],
        )

        assert len(result["agents"]) == 3
        assert "00-meta" in result["agents"]
        assert "01-architect" in result["agents"]
        assert "05-test" in result["agents"]

        # Verify only requested agents have directories
        feature_path = test_ai_history_repo / feature_id
        assert (feature_path / "00-meta").exists()
        assert (feature_path / "01-architect").exists()
        assert (feature_path / "05-test").exists()
        assert not (feature_path / "02-openapi").exists()
        assert not (feature_path / "03-ui").exists()


class TestErrorHandling:
    """Tests for error handling in workflows."""

    def test_duplicate_feature_initialization(self, test_git_repo, test_ai_history_repo):
        """Test error when initializing feature that already exists."""
        feature_id = "feat-duplicate"

        # Initialize once
        initialize_feature(
            feature_id=feature_id,
            code_repo_path=test_git_repo,
            ai_history_path=test_ai_history_repo,
            agents=["00-meta"],
        )

        # Try to initialize again
        with pytest.raises(ValueError, match="already exists"):
            initialize_feature(
                feature_id=feature_id,
                code_repo_path=test_git_repo,
                ai_history_path=test_ai_history_repo,
                agents=["00-meta"],
            )

    def test_invalid_feature_id(self, test_git_repo, test_ai_history_repo):
        """Test error with invalid feature ID."""
        with pytest.raises(ValueError, match="must start with a letter"):
            initialize_feature(
                feature_id="123-invalid",
                code_repo_path=test_git_repo,
                ai_history_path=test_ai_history_repo,
                agents=["00-meta"],
            )

    def test_submit_to_nonexistent_feature(self, test_ai_history_repo):
        """Test submitting to non-existent feature creates directories."""
        # write_prompt creates directories if they don't exist
        # This is intentional - features can be created on-the-fly
        prompt_file = write_prompt(
            ai_history_path=test_ai_history_repo,
            feature_id="nonexistent",
            agent_id="00-meta",
            prompt_task=PromptTask(
                feature_id="nonexistent",
                agent_id="00-meta",
                prompt_text="Test",
                spec_version="1.0.0",
            ),
        )

        # Verify prompt was written and directories were created
        assert prompt_file.exists()
        assert (test_ai_history_repo / "nonexistent" / "00-meta" / "in").exists()
