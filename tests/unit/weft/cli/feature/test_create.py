"""Tests for feature create command with Agent 00 loop."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from weft.cli.feature.create import display_spec, feature_create


class TestDisplaySpec:
    """Tests for display_spec helper."""

    def test_display_spec_formats_output(self, capsys):
        """Test spec is displayed with formatting."""
        spec_content = "# Test Spec\n\nThis is a test specification."

        display_spec(spec_content)

        captured = capsys.readouterr()
        assert "FEATURE SPECIFICATION" in captured.out
        assert "# Test Spec" in captured.out
        assert "=" * 70 in captured.out


@pytest.mark.timeout(30)
class TestFeatureCreateCommand:
    """Tests for feature-create command."""

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.create.initialize_feature")
    @patch("weft.cli.feature.create.submit_prompt_to_agent")
    @patch("weft.cli.feature.create.wait_for_agent_result")
    def test_feature_create_new_feature_accept_first_try(
        self,
        mock_wait,
        mock_submit,
        mock_init,
        mock_settings,
        tmp_path: Path,
    ):
        """Test creating new feature and accepting spec on first try."""
        # Setup mock settings
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )

        # Mock agent prompt submission and output
        mock_submit.return_value = tmp_path / "prompt.md"
        mock_wait.return_value = "# Spec\n\nFeature specification content"

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature"],
            input="Add user authentication\nyes\n",
        )

        assert result.exit_code == 0
        assert "Creating feature: test-feature" in result.output
        assert "Creating worktree" in result.output
        assert "Submitting to Agent 00" in result.output
        assert "Agent 00 has generated the specification" in result.output
        assert "Feature spec accepted" in result.output
        assert "weft feature start test-feature" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.create.initialize_feature")
    @patch("weft.cli.feature.create.submit_prompt_to_agent")
    @patch("weft.cli.feature.create.wait_for_agent_result")
    def test_feature_create_with_description_flag(
        self,
        mock_wait,
        mock_submit,
        mock_init,
        mock_settings,
        tmp_path: Path,
    ):
        """Test creating feature with --description flag."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )
        mock_submit.return_value = tmp_path / "prompt.md"
        mock_wait.return_value = "# Spec"

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature", "--description", "Add JWT auth"],
            input="yes\n",
        )

        assert result.exit_code == 0
        assert "Feature spec accepted" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.create.initialize_feature")
    @patch("weft.cli.feature.create.submit_prompt_to_agent")
    @patch("weft.cli.feature.create.wait_for_agent_result")
    def test_feature_create_iteration_workflow(
        self,
        mock_wait,
        mock_submit,
        mock_init,
        mock_settings,
        tmp_path: Path,
    ):
        """Test iterating on spec before acceptance."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )

        # Mock submit to return different prompt files for each iteration
        mock_submit.side_effect = [tmp_path / "prompt_v1.md", tmp_path / "prompt_v2.md"]
        # First iteration returns spec v1, second returns spec v2
        mock_wait.side_effect = [
            "# Spec v1\n\nInitial spec",
            "# Spec v2\n\nRefined spec",
        ]

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature"],
            input="Add user auth\niterate\nAdd OAuth support\nyes\n",
        )

        assert result.exit_code == 0
        assert "Spec v1" in result.output
        assert "Spec v2" in result.output
        assert "iteration v2" in result.output
        assert mock_wait.call_count == 2

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.create.initialize_feature")
    @patch("weft.cli.feature.create.submit_prompt_to_agent")
    @patch("weft.cli.feature.create.wait_for_agent_result")
    def test_feature_create_user_cancels(
        self,
        mock_wait,
        mock_submit,
        mock_init,
        mock_settings,
        tmp_path: Path,
    ):
        """Test user cancelling after seeing spec."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )
        mock_submit.return_value = tmp_path / "prompt.md"
        mock_wait.return_value = "# Spec"

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature"],
            input="Add feature\nno\n",
        )

        assert result.exit_code != 0
        assert "Feature creation cancelled" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.create.initialize_feature")
    @patch("weft.cli.feature.create.submit_prompt_to_agent")
    @patch("weft.cli.feature.create.wait_for_agent_result")
    def test_feature_create_timeout_retry(
        self,
        mock_wait,
        mock_submit,
        mock_init,
        mock_settings,
        tmp_path: Path,
    ):
        """Test timeout and retry workflow."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )

        mock_submit.return_value = tmp_path / "prompt.md"
        # First wait times out, second succeeds
        mock_wait.side_effect = [None, "# Spec\n\nContent"]

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature"],
            input="Add feature\ny\nyes\n",  # y to retry, yes to accept
        )

        assert result.exit_code == 0
        assert "Timeout waiting for Agent 00" in result.output
        assert "Retry waiting?" in result.output
        assert "Feature spec accepted" in result.output
        assert mock_wait.call_count == 2

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.create.initialize_feature")
    @patch("weft.cli.feature.create.submit_prompt_to_agent")
    @patch("weft.cli.feature.create.wait_for_agent_result")
    def test_feature_create_timeout_no_retry(
        self,
        mock_wait,
        mock_submit,
        mock_init,
        mock_settings,
        tmp_path: Path,
    ):
        """Test user choosing not to retry after timeout."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )
        mock_submit.return_value = tmp_path / "prompt.md"
        mock_wait.return_value = None  # Timeout

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature"],
            input="Add feature\nn\n",  # n to not retry
        )

        assert result.exit_code != 0
        assert "Timeout waiting for Agent 00" in result.output
        assert "You can manually check" in result.output

    @patch("weft.cli.utils.get_settings")
    def test_feature_create_resume_existing(
        self,
        mock_settings,
        tmp_path: Path,
    ):
        """Test resuming existing feature with spec."""
        # Setup existing feature structure
        code_path = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        mock_settings.return_value = Mock(
            code_repo_path=code_path,
            ai_history_path=ai_history,
        )

        # Create existing worktree and history
        worktree = code_path.parent / "worktrees/test-feature"
        worktree.mkdir(parents=True)

        meta_out = ai_history / "test-feature" / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "test_result.md").write_text("# Existing Spec")

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature"],
            input="y\naccept\n",  # y to resume, accept the spec
        )

        assert result.exit_code == 0
        assert "Feature 'test-feature' already exists" in result.output
        assert "Resume with existing feature?" in result.output
        assert "Found existing spec" in result.output
        assert "Feature spec accepted" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.create.submit_prompt_to_agent")
    @patch("weft.cli.feature.create.wait_for_agent_result")
    def test_feature_create_resume_and_iterate(
        self,
        mock_wait,
        mock_submit,
        mock_settings,
        tmp_path: Path,
    ):
        """Test resuming existing feature and iterating on spec."""
        # Setup existing feature
        code_path = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        mock_settings.return_value = Mock(
            code_repo_path=code_path,
            ai_history_path=ai_history,
        )

        worktree = code_path.parent / "worktrees/test-feature"
        worktree.mkdir(parents=True)

        meta_out = ai_history / "test-feature" / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "test_result.md").write_text("# Existing Spec v1")

        # Mock agent submission to return None (timeout)
        mock_submit.return_value = tmp_path / "prompt.md"
        mock_wait.return_value = None

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature"],
            input="y\niterate\nAdd more details\nn\n",  # Resume, iterate, don't retry
        )

        # Check that iteration was attempted
        assert "Feature 'test-feature' already exists" in result.output
        assert "Found existing spec" in result.output
        assert "iterate" in result.output.lower()

    @patch("weft.cli.utils.get_settings")
    def test_feature_create_settings_error(self, mock_settings):
        """Test error when settings cannot be loaded."""
        mock_settings.side_effect = ValueError("Settings missing")

        runner = CliRunner()
        result = runner.invoke(feature_create, ["test-feature"])

        assert result.exit_code != 0
        assert "Settings missing" in result.output

    @patch("weft.cli.feature.create.initialize_feature")
    @patch("weft.cli.utils.get_settings")
    def test_feature_create_after_dropped(self, mock_settings, mock_initialize, tmp_path: Path):
        """Test re-creating a feature that was previously dropped."""
        code_path = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        mock_settings.return_value = Mock(
            code_repo_path=code_path,
            ai_history_path=ai_history,
        )

        # Setup dropped feature marker
        feature_history = ai_history / "test-feature"
        feature_history.mkdir(parents=True)
        dropped_marker = feature_history / "DROPPED.md"
        dropped_marker.write_text("# Feature Dropped\nReason: Test")

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature", "--description", "Test feature"],
            input="y\n",  # Confirm re-creation
        )

        # Should detect dropped feature and ask for confirmation
        assert "previously dropped" in result.output
        assert "Re-create feature" in result.output
        # Dropped marker should be removed (checked by file not existing)
        assert not dropped_marker.exists()

    @patch("weft.cli.utils.get_settings")
    def test_feature_create_after_dropped_cancelled(self, mock_settings, tmp_path: Path):
        """Test canceling re-creation of dropped feature."""
        code_path = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        mock_settings.return_value = Mock(
            code_repo_path=code_path,
            ai_history_path=ai_history,
        )

        # Setup dropped feature marker
        feature_history = ai_history / "test-feature"
        feature_history.mkdir(parents=True)
        dropped_marker = feature_history / "DROPPED.md"
        dropped_marker.write_text("# Feature Dropped\nReason: Test")

        runner = CliRunner()
        result = runner.invoke(
            feature_create,
            ["test-feature"],
            input="n\n",  # Cancel re-creation
        )

        # Should cancel and marker should still exist
        assert "previously dropped" in result.output
        assert "Cancelled" in result.output
        assert dropped_marker.exists()


@pytest.mark.timeout(30)
class TestFeatureCreateIntegration:
    """Integration tests for feature create workflow."""

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.create.initialize_feature")
    @patch("weft.cli.feature.create.submit_prompt_to_agent")
    @patch("weft.cli.feature.create.wait_for_agent_result")
    def test_full_create_workflow_with_mocked_agent(
        self,
        mock_wait,
        mock_submit,
        mock_init,
        mock_settings,
        tmp_path: Path,
    ):
        """Test complete workflow from creation to acceptance with mocked agent output."""
        code_path = tmp_path / "code"
        ai_history = tmp_path / "ai-history"

        mock_settings.return_value = Mock(
            code_repo_path=code_path,
            ai_history_path=ai_history,
        )

        # Mock agent to return None (timeout)
        prompt_file = ai_history / "user-auth" / "00-meta" / "in" / "user-auth_prompt_v1.md"
        mock_submit.return_value = prompt_file
        mock_wait.return_value = None

        runner = CliRunner()

        # Start the command
        result = runner.invoke(
            feature_create,
            ["user-auth", "-d", "Add JWT authentication"],
            input="n\n",  # Will timeout waiting for agent, say no to retry
        )

        # Check that it got to the waiting stage
        assert "Submitting to Agent 00" in result.output
        assert "Waiting for Agent 00" in result.output

        # Verify prompt submission was attempted
        mock_submit.assert_called_once()
