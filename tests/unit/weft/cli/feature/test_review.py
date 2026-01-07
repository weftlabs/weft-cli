"""Tests for feature review command."""

from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from weft.cli.feature.review import (
    extract_code_blocks,
    get_agent_outputs,
    review,
)
from weft.state import FeatureState, FeatureStatus


class TestGetAgentOutputs:
    """Tests for get_agent_outputs helper function."""

    def test_get_agent_outputs_with_results(self, tmp_path: Path):
        """Test getting agent outputs when results exist."""
        ai_history = tmp_path / "ai-history"
        feature_name = "test-feature"

        # Create agent output directories with results
        for agent_id in ["00-meta", "01-architect"]:
            out_dir = ai_history / feature_name / agent_id / "out"
            out_dir.mkdir(parents=True)
            (out_dir / f"{feature_name}_result.md").write_text(f"Output from {agent_id}")

        outputs = get_agent_outputs(feature_name, ai_history)

        assert outputs["00-meta"] == "Output from 00-meta"
        assert outputs["01-architect"] == "Output from 01-architect"
        assert outputs["02-openapi"] is None
        assert outputs["03-ui"] is None
        assert outputs["04-integration"] is None
        assert outputs["05-test"] is None

    def test_get_agent_outputs_no_results(self, tmp_path: Path):
        """Test getting agent outputs when no results exist."""
        ai_history = tmp_path / "ai-history"
        feature_name = "test-feature"

        outputs = get_agent_outputs(feature_name, ai_history)

        assert all(output is None for output in outputs.values())
        assert len(outputs) == 6

    def test_get_agent_outputs_multiple_results_uses_latest(self, tmp_path: Path):
        """Test that latest result is used when multiple exist."""
        import time

        ai_history = tmp_path / "ai-history"
        feature_name = "test-feature"
        out_dir = ai_history / feature_name / "00-meta" / "out"
        out_dir.mkdir(parents=True)

        # Create older result
        old_result = out_dir / "old_result.md"
        old_result.write_text("Old output")
        time.sleep(0.01)

        # Create newer result
        new_result = out_dir / "new_result.md"
        new_result.write_text("New output")

        outputs = get_agent_outputs(feature_name, ai_history)

        assert outputs["00-meta"] == "New output"


class TestExtractCodeBlocks:
    """Tests for extract_code_blocks helper function."""

    def test_extract_code_blocks_with_language(self):
        """Test extracting code blocks with language specified."""
        text = """
# Example

```python
def hello():
    print("world")
```

Some text

```javascript
console.log("hello");
```
"""
        blocks = extract_code_blocks(text)

        assert len(blocks) == 2
        assert blocks[0] == ("python", 'def hello():\n    print("world")')
        assert blocks[1] == ("javascript", 'console.log("hello");')

    def test_extract_code_blocks_without_language(self):
        """Test extracting code blocks without language."""
        text = """
```
plain code
```
"""
        blocks = extract_code_blocks(text)

        assert len(blocks) == 1
        assert blocks[0] == (None, "plain code")

    def test_extract_code_blocks_none(self):
        """Test with no code blocks."""
        text = "Just plain text"
        blocks = extract_code_blocks(text)

        assert len(blocks) == 0


class TestReviewCommand:
    """Tests for feature review CLI command."""

    @patch("weft.cli.feature.review.handle_accept")
    @patch("weft.cli.feature.review.show_test_results")
    @patch("weft.cli.feature.review.show_ai_generated_files")
    @patch("weft.cli.feature.review.display_summary")
    @patch("weft.cli.feature.review.get_agent_outputs")
    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_accept_flow(
        self,
        mock_settings,
        mock_get_state,
        mock_get_outputs,
        mock_display,
        mock_show_files,
        mock_show_tests,
        mock_handle_accept,
        tmp_path: Path,
    ):
        """Test review command with accept choice."""
        # Setup
        code_repo = tmp_path / "code"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.READY,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )
        mock_get_outputs.return_value = {"00-meta": "spec", "01-architect": "arch"}
        mock_show_tests.return_value = True

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature"], input="accept\n")

        assert result.exit_code == 0
        mock_handle_accept.assert_called_once()

    @patch("weft.cli.feature.review.handle_drop")
    @patch("weft.cli.feature.review.show_test_results")
    @patch("weft.cli.feature.review.show_ai_generated_files")
    @patch("weft.cli.feature.review.display_summary")
    @patch("weft.cli.feature.review.get_agent_outputs")
    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_drop_flow(
        self,
        mock_settings,
        mock_get_state,
        mock_get_outputs,
        mock_display,
        mock_show_files,
        mock_show_tests,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test review command with drop choice."""
        code_repo = tmp_path / "code"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.READY,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )
        mock_get_outputs.return_value = {}
        mock_show_tests.return_value = True

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature"], input="drop\n")

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once()

    @patch("weft.cli.feature.review.show_test_results")
    @patch("weft.cli.feature.review.show_ai_generated_files")
    @patch("weft.cli.feature.review.display_summary")
    @patch("weft.cli.feature.review.get_agent_outputs")
    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_continue_flow(
        self,
        mock_settings,
        mock_get_state,
        mock_get_outputs,
        mock_display,
        mock_show_files,
        mock_show_tests,
        tmp_path: Path,
    ):
        """Test review command with continue choice."""
        code_repo = tmp_path / "code"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.IN_PROGRESS,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )
        mock_get_outputs.return_value = {}
        mock_show_tests.return_value = True

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature"], input="continue\n")

        assert result.exit_code == 0
        assert "Continue working" in result.output

    @patch("weft.cli.utils.get_settings")
    def test_review_settings_error(self, mock_settings):
        """Test review command when settings cannot be loaded."""
        mock_settings.side_effect = ValueError("Settings missing")

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature"])

        assert result.exit_code == 1
        assert "Settings missing" in result.output

    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_completed_feature_error(self, mock_settings, mock_get_state, tmp_path: Path):
        """Test review fails on completed feature."""
        code_repo = tmp_path / "code"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.COMPLETED,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature"])

        assert result.exit_code == 1
        assert "terminal state" in result.output

    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_dropped_feature_error(self, mock_settings, mock_get_state, tmp_path: Path):
        """Test review fails on dropped feature."""
        code_repo = tmp_path / "code"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.DROPPED,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature"])

        assert result.exit_code == 1
        assert "terminal state" in result.output

    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_worktree_not_found(self, mock_settings, mock_get_state, tmp_path: Path):
        """Test review fails when worktree doesn't exist."""
        code_repo = tmp_path / "code"

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.IN_PROGRESS,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature"])

        assert result.exit_code == 1
        assert "Worktree not found" in result.output

    @patch("weft.cli.feature.review.handle_accept")
    @patch("weft.cli.feature.review.show_test_results")
    @patch("weft.cli.feature.review.show_ai_generated_files")
    @patch("weft.cli.feature.review.display_summary")
    @patch("weft.cli.feature.review.get_agent_outputs")
    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_with_base_branch_option(
        self,
        mock_settings,
        mock_get_state,
        mock_get_outputs,
        mock_display,
        mock_show_files,
        mock_show_tests,
        mock_handle_accept,
        tmp_path: Path,
    ):
        """Test review command with custom base branch."""
        code_repo = tmp_path / "code"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.READY,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )
        mock_get_outputs.return_value = {}
        mock_show_tests.return_value = True

        runner = CliRunner()
        result = runner.invoke(
            review, ["test-feature", "--base-branch", "develop"], input="accept\n"
        )

        assert result.exit_code == 0
        # Verify base_branch was passed to handle_accept
        call_args = mock_handle_accept.call_args
        assert call_args[0][4] == "develop"  # base_branch is 5th argument

    @patch("weft.cli.feature.review.handle_drop")
    @patch("weft.cli.feature.review.show_test_results")
    @patch("weft.cli.feature.review.show_ai_generated_files")
    @patch("weft.cli.feature.review.display_summary")
    @patch("weft.cli.feature.review.get_agent_outputs")
    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_with_delete_history_flag(
        self,
        mock_settings,
        mock_get_state,
        mock_get_outputs,
        mock_display,
        mock_show_files,
        mock_show_tests,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test review command with delete history flag."""
        code_repo = tmp_path / "code"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.READY,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )
        mock_get_outputs.return_value = {}
        mock_show_tests.return_value = True

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature", "--delete-history"], input="drop\n")

        assert result.exit_code == 0
        # Verify delete_history was passed to handle_drop
        call_args = mock_handle_drop.call_args
        assert call_args[0][4] is True  # delete_history is 5th argument

    @patch("weft.cli.feature.review.handle_drop")
    @patch("weft.cli.feature.review.show_test_results")
    @patch("weft.cli.feature.review.show_ai_generated_files")
    @patch("weft.cli.feature.review.display_summary")
    @patch("weft.cli.feature.review.get_agent_outputs")
    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_with_reason_option(
        self,
        mock_settings,
        mock_get_state,
        mock_get_outputs,
        mock_display,
        mock_show_files,
        mock_show_tests,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test review command with drop reason."""
        code_repo = tmp_path / "code"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.READY,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )
        mock_get_outputs.return_value = {}
        mock_show_tests.return_value = True

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature", "--reason", "Not needed"], input="drop\n")

        assert result.exit_code == 0
        # Verify reason was passed to handle_drop
        call_args = mock_handle_drop.call_args
        assert call_args[0][5] == "Not needed"  # reason is 6th argument

    @patch("weft.cli.feature.review.show_test_results")
    @patch("weft.cli.feature.review.show_ai_generated_files")
    @patch("weft.cli.feature.review.display_summary")
    @patch("weft.cli.feature.review.get_agent_outputs")
    @patch("weft.cli.feature.review.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    def test_review_shows_test_failure_warning(
        self,
        mock_settings,
        mock_get_state,
        mock_get_outputs,
        mock_display,
        mock_show_files,
        mock_show_tests,
        tmp_path: Path,
    ):
        """Test review shows warning when tests fail."""
        code_repo = tmp_path / "code"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=tmp_path / "ai-history",
        )
        mock_get_state.return_value = FeatureState(
            feature_name="test-feature",
            status=FeatureStatus.IN_PROGRESS,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )
        mock_get_outputs.return_value = {}
        mock_show_tests.return_value = False  # Tests failed

        runner = CliRunner()
        result = runner.invoke(review, ["test-feature"], input="continue\n")

        assert result.exit_code == 0
        assert "Some tests failed" in result.output
