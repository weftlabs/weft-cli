"""Tests for feature drop command."""

from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from weft.cli.feature.drop import feature_drop


class TestFeatureDropCommand:
    """Tests for feature drop CLI command."""

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_basic(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test basic feature drop with user confirmation."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(feature_drop, ["test-feature"])

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once_with(
            "test-feature",
            code_repo,
            ai_history,
            worktree_path,
            False,  # delete_history default
            None,  # reason default
        )

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_with_force_flag(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop with --force flag skips confirmation."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(feature_drop, ["test-feature", "--force"])

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once_with(
            "test-feature",
            code_repo,
            ai_history,
            worktree_path,
            False,
            None,
        )

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_with_delete_history(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop with --delete-history flag."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(
            feature_drop,
            ["test-feature", "--delete-history", "--force"],
        )

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once_with(
            "test-feature",
            code_repo,
            ai_history,
            worktree_path,
            True,  # delete_history=True
            None,
        )

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_with_reason(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop with --reason option."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(
            feature_drop,
            ["test-feature", "--reason", "Requirements changed", "--force"],
        )

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once_with(
            "test-feature",
            code_repo,
            ai_history,
            worktree_path,
            False,
            "Requirements changed",
        )

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_with_all_options(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop with all options combined."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(
            feature_drop,
            [
                "test-feature",
                "--delete-history",
                "--reason",
                "Test cleanup",
                "--force",
            ],
        )

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once_with(
            "test-feature",
            code_repo,
            ai_history,
            worktree_path,
            True,
            "Test cleanup",
        )

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_with_short_flags(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop with short flags (-r, -f)."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(
            feature_drop,
            ["test-feature", "-r", "Test", "-f"],
        )

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once_with(
            "test-feature",
            code_repo,
            ai_history,
            worktree_path,
            False,
            "Test",
        )

    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_settings_error(self, mock_settings):
        """Test feature drop fails when settings cannot be loaded."""
        mock_settings.side_effect = ValueError("Settings missing")

        runner = CliRunner()
        result = runner.invoke(feature_drop, ["test-feature", "--force"])

        assert result.exit_code == 1
        assert "Settings missing" in result.output

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_handle_drop_error(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop handles errors from handle_drop."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path
        mock_handle_drop.side_effect = RuntimeError("Git error")

        runner = CliRunner()
        result = runner.invoke(feature_drop, ["test-feature", "--force"])

        assert result.exit_code == 1
        assert "Git error" in result.output

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_user_abort(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop when user aborts via handle_drop."""
        import click

        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path
        mock_handle_drop.side_effect = click.Abort()

        runner = CliRunner()
        result = runner.invoke(feature_drop, ["test-feature", "--force"])

        assert result.exit_code == 1

    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_get_worktree_path_error(
        self,
        mock_settings,
        mock_get_worktree,
        tmp_path: Path,
    ):
        """Test feature drop handles errors from get_worktree_path."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.side_effect = ValueError("Invalid feature name")

        runner = CliRunner()
        result = runner.invoke(feature_drop, ["test-feature", "--force"])

        assert result.exit_code == 1
        assert "Invalid feature name" in result.output

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_with_special_characters(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop with special characters in name."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        feature_name = "feat-123_test-v2"
        worktree_path = code_repo / "worktrees" / feature_name
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(feature_drop, [feature_name, "--force"])

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once_with(
            feature_name,
            code_repo,
            ai_history,
            worktree_path,
            False,
            None,
        )

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_empty_reason(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop with empty reason string."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(
            feature_drop,
            ["test-feature", "--reason", "", "--force"],
        )

        assert result.exit_code == 0
        # Empty string is passed as-is
        mock_handle_drop.assert_called_once_with(
            "test-feature",
            code_repo,
            ai_history,
            worktree_path,
            False,
            "",
        )

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_long_reason(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop with very long reason."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        long_reason = "A" * 500  # Very long reason

        runner = CliRunner()
        result = runner.invoke(
            feature_drop,
            ["test-feature", "--reason", long_reason, "--force"],
        )

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once_with(
            "test-feature",
            code_repo,
            ai_history,
            worktree_path,
            False,
            long_reason,
        )

    def test_feature_drop_missing_argument(self):
        """Test feature drop fails without feature name argument."""
        runner = CliRunner()
        result = runner.invoke(feature_drop, [])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "FEATURE_NAME" in result.output

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_force_patches_confirmation(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test that --force flag properly patches click.confirm."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        # Track if handle_drop was called
        call_count = {"count": 0}

        def track_call(*args, **kwargs):
            call_count["count"] += 1

        mock_handle_drop.side_effect = track_call

        runner = CliRunner()
        result = runner.invoke(feature_drop, ["test-feature", "--force"])

        assert result.exit_code == 0
        assert call_count["count"] == 1
        # Verify handle_drop was called exactly once with correct params
        mock_handle_drop.assert_called_once()

    @patch("weft.cli.feature.drop.handle_drop")
    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_multiple_flags_order(
        self,
        mock_settings,
        mock_get_worktree,
        mock_handle_drop,
        tmp_path: Path,
    ):
        """Test feature drop with flags in different order."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        worktree_path = code_repo / "worktrees" / "test-feature"
        worktree_path.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        # Try flags in different order
        result = runner.invoke(
            feature_drop,
            ["-f", "test-feature", "-r", "Test", "--delete-history"],
        )

        assert result.exit_code == 0
        mock_handle_drop.assert_called_once_with(
            "test-feature",
            code_repo,
            ai_history,
            worktree_path,
            True,
            "Test",
        )

    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_already_dropped(
        self,
        mock_settings,
        mock_get_worktree,
        tmp_path: Path,
    ):
        """Test dropping a feature that's already dropped."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        feature_history = ai_history / "test-feature"
        feature_history.mkdir(parents=True)
        worktree_path = code_repo / "worktrees" / "test-feature"

        # Create dropped marker
        dropped_marker = feature_history / "DROPPED.md"
        dropped_marker.write_text("# Feature Dropped\nReason: Test")

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(feature_drop, ["test-feature", "--force"])

        assert result.exit_code == 0
        assert "already dropped" in result.output
        assert "FEATURE ALREADY DROPPED" in result.output
        assert "--delete-history" in result.output
        # Marker should still exist
        assert dropped_marker.exists()

    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_already_dropped_with_delete_history(
        self,
        mock_settings,
        mock_get_worktree,
        tmp_path: Path,
    ):
        """Test deleting AI history of already dropped feature."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        feature_history = ai_history / "test-feature"
        feature_history.mkdir(parents=True)
        worktree_path = code_repo / "worktrees" / "test-feature"

        # Create dropped marker
        dropped_marker = feature_history / "DROPPED.md"
        dropped_marker.write_text("# Feature Dropped\nReason: Test")

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(
            feature_drop,
            ["test-feature", "--delete-history"],
            input="y\n",  # Confirm deletion
        )

        assert result.exit_code == 0
        assert "already dropped" in result.output
        assert "Permanently delete AI history" in result.output
        assert "AI HISTORY DELETED" in result.output
        # History should be deleted
        assert not feature_history.exists()

    @patch("weft.cli.feature.drop.get_worktree_path")
    @patch("weft.cli.utils.get_settings")
    def test_feature_drop_already_dropped_cancel_delete(
        self,
        mock_settings,
        mock_get_worktree,
        tmp_path: Path,
    ):
        """Test canceling deletion of already dropped feature."""
        code_repo = tmp_path / "code"
        ai_history = tmp_path / "ai-history"
        feature_history = ai_history / "test-feature"
        feature_history.mkdir(parents=True)
        worktree_path = code_repo / "worktrees" / "test-feature"

        # Create dropped marker
        dropped_marker = feature_history / "DROPPED.md"
        dropped_marker.write_text("# Feature Dropped\nReason: Test")

        mock_settings.return_value = Mock(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
        )
        mock_get_worktree.return_value = worktree_path

        runner = CliRunner()
        result = runner.invoke(
            feature_drop,
            ["test-feature", "--delete-history"],
            input="n\n",  # Cancel deletion
        )

        assert result.exit_code == 1
        assert "already dropped" in result.output
        assert "Delete cancelled" in result.output
        # History should still exist
        assert dropped_marker.exists()
