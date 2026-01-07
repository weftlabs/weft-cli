"""Tests for feature list command."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from weft.cli.feature.list import feature_list, humanize_time
from weft.git.worktree import WorktreeInfo
from weft.state import FeatureState, FeatureStatus


class TestHumanizeTime:
    """Tests for humanize_time helper."""

    def test_humanize_time_just_now(self):
        """Test time less than 1 minute."""
        dt = datetime.now() - timedelta(seconds=30)
        assert humanize_time(dt) == "just now"

    def test_humanize_time_minutes(self):
        """Test time in minutes."""
        dt = datetime.now() - timedelta(minutes=15)
        assert humanize_time(dt) == "15m ago"

    def test_humanize_time_hours(self):
        """Test time in hours."""
        dt = datetime.now() - timedelta(hours=3)
        assert humanize_time(dt) == "3h ago"

    def test_humanize_time_yesterday(self):
        """Test yesterday."""
        dt = datetime.now() - timedelta(days=1, hours=2)
        assert humanize_time(dt) == "yesterday"

    def test_humanize_time_days(self):
        """Test days within a week."""
        dt = datetime.now() - timedelta(days=5)
        assert humanize_time(dt) == "5d ago"

    def test_humanize_time_old(self):
        """Test dates older than a week."""
        dt = datetime.now() - timedelta(days=30)
        result = humanize_time(dt)
        # Should be formatted as YYYY-MM-DD
        assert len(result) == 10
        assert result[4] == "-"
        assert result[7] == "-"


class TestFeatureListCommand:
    """Tests for feature-list CLI command."""

    @patch("weft.cli.feature.list.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_feature_list_shows_worktrees(
        self, mock_list_worktrees, mock_settings, mock_get_state, tmp_path: Path
    ):
        """Test listing shows all feature worktrees."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
        )

        # Mock feature states
        def mock_state(feature_name):
            return FeatureState(
                feature_name=feature_name,
                status=FeatureStatus.IN_PROGRESS,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                transitions=[],
            )

        mock_get_state.side_effect = mock_state

        # Mock worktrees
        mock_list_worktrees.return_value = [
            WorktreeInfo(
                path=tmp_path / "worktrees" / "user-auth",
                branch="feature/user-auth",
                feature_id="user-auth",
                created_at=datetime.now(),
            ),
            WorktreeInfo(
                path=tmp_path / "worktrees" / "dashboard",
                branch="feature/dashboard",
                feature_id="dashboard",
                created_at=datetime.now(),
            ),
        ]

        runner = CliRunner()
        result = runner.invoke(feature_list)

        assert result.exit_code == 0
        assert "user-auth" in result.output
        assert "dashboard" in result.output
        assert "Total: 2" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_feature_list_no_features(self, mock_list_worktrees, mock_settings, tmp_path: Path):
        """Test listing when no features exist."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
        )

        mock_list_worktrees.return_value = []

        runner = CliRunner()
        result = runner.invoke(feature_list)

        assert result.exit_code == 0
        assert "No active features found" in result.output
        assert "--all" in result.output

    @patch("weft.cli.feature.list.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_feature_list_filters_non_feature_branches(
        self, mock_list_worktrees, mock_settings, mock_get_state, tmp_path: Path
    ):
        """Test only feature branches are shown."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
        )

        # Mock feature state
        mock_get_state.return_value = FeatureState(
            feature_name="user-auth",
            status=FeatureStatus.IN_PROGRESS,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )

        # Mock worktrees including non-feature branches
        mock_list_worktrees.return_value = [
            WorktreeInfo(
                path=tmp_path / "worktrees" / "user-auth",
                branch="feature/user-auth",
                feature_id="user-auth",
                created_at=datetime.now(),
            ),
            WorktreeInfo(
                path=tmp_path / "worktrees" / "main",
                branch="main",
                feature_id="main",
                created_at=datetime.now(),
            ),
            WorktreeInfo(
                path=tmp_path / "worktrees" / "hotfix",
                branch="hotfix/urgent",
                feature_id="urgent",
                created_at=datetime.now(),
            ),
        ]

        runner = CliRunner()
        result = runner.invoke(feature_list)

        assert result.exit_code == 0
        assert "user-auth" in result.output
        assert "main" not in result.output
        assert "hotfix" not in result.output

    @patch("weft.cli.feature.list.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_feature_list_sort_by_name(
        self, mock_list_worktrees, mock_settings, mock_get_state, tmp_path: Path
    ):
        """Test sorting by name."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
        )

        # Mock feature states
        def mock_state(feature_name):
            return FeatureState(
                feature_name=feature_name,
                status=FeatureStatus.IN_PROGRESS,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                transitions=[],
            )

        mock_get_state.side_effect = mock_state

        mock_list_worktrees.return_value = [
            WorktreeInfo(
                path=tmp_path / "zebra",
                branch="feature/zebra",
                feature_id="zebra",
                created_at=datetime.now(),
            ),
            WorktreeInfo(
                path=tmp_path / "alpha",
                branch="feature/alpha",
                feature_id="alpha",
                created_at=datetime.now(),
            ),
            WorktreeInfo(
                path=tmp_path / "beta",
                branch="feature/beta",
                feature_id="beta",
                created_at=datetime.now(),
            ),
        ]

        runner = CliRunner()
        result = runner.invoke(feature_list, ["--sort-by", "name"])

        assert result.exit_code == 0
        lines = result.output.split("\n")
        # Find the lines with feature names
        feature_lines = [line for line in lines if "feature/" in line]
        # Should be alphabetically sorted - check order by checking if feature names appear in order
        assert len(feature_lines) == 3
        assert "alpha" in feature_lines[0]
        assert "beta" in feature_lines[1]
        assert "zebra" in feature_lines[2]

    @patch("weft.cli.feature.list.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_feature_list_sort_by_status(
        self, mock_list_worktrees, mock_settings, mock_get_state, tmp_path: Path
    ):
        """Test sorting by status."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
        )

        # Mock different statuses for different features
        def mock_state(feature_name):
            status = (
                FeatureStatus.IN_PROGRESS if "progress" in feature_name else FeatureStatus.DRAFT
            )
            return FeatureState(
                feature_name=feature_name,
                status=status,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                transitions=[],
            )

        mock_get_state.side_effect = mock_state

        mock_list_worktrees.return_value = [
            WorktreeInfo(
                path=tmp_path / "p",
                branch="feature/progress-feature",
                feature_id="progress-feature",
                created_at=datetime.now(),
            ),
            WorktreeInfo(
                path=tmp_path / "d",
                branch="feature/draft-feature",
                feature_id="draft-feature",
                created_at=datetime.now(),
            ),
        ]

        runner = CliRunner()
        result = runner.invoke(feature_list, ["--sort-by", "status"])

        assert result.exit_code == 0
        # In-progress should come before draft
        progress_idx = result.output.index("progress-feature")
        draft_idx = result.output.index("draft-feature")
        assert progress_idx < draft_idx

    @patch("weft.cli.feature.list.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_feature_list_status_icons(
        self, mock_list_worktrees, mock_settings, mock_get_state, tmp_path: Path
    ):
        """Test status icons are displayed."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
        )

        # Mock in-progress state
        mock_get_state.return_value = FeatureState(
            feature_name="test",
            status=FeatureStatus.IN_PROGRESS,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )

        mock_list_worktrees.return_value = [
            WorktreeInfo(
                path=tmp_path / "test",
                branch="feature/test",
                feature_id="test",
                created_at=datetime.now(),
            ),
        ]

        runner = CliRunner()
        result = runner.invoke(feature_list)

        assert result.exit_code == 0
        # Should have in-progress icon and status
        assert "⏳" in result.output
        assert "in-progress" in result.output

    @patch("weft.cli.utils.get_settings")
    def test_feature_list_settings_error(self, mock_settings):
        """Test error when settings cannot be loaded."""
        mock_settings.side_effect = ValueError("Settings missing")

        runner = CliRunner()
        result = runner.invoke(feature_list)

        assert result.exit_code != 0
        assert "Settings missing" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_feature_list_worktree_error(self, mock_list_worktrees, mock_settings, tmp_path: Path):
        """Test error handling when listing worktrees fails."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
        )

        mock_list_worktrees.side_effect = Exception("Git error")

        runner = CliRunner()
        result = runner.invoke(feature_list)

        assert result.exit_code != 0
        assert "Error listing worktrees" in result.output


class TestFeatureListIntegration:
    """Integration tests for feature list."""

    @patch("weft.cli.feature.list.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_full_feature_list_workflow(
        self, mock_list_worktrees, mock_settings, mock_get_state, tmp_path: Path
    ):
        """Test complete feature list display."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
        )

        # Mock feature states with different statuses
        def mock_state(feature_name):
            status = FeatureStatus.DRAFT if "draft" in feature_name else FeatureStatus.IN_PROGRESS
            return FeatureState(
                feature_name=feature_name,
                status=status,
                created_at=datetime.now(),
                last_activity=datetime.now(),
                transitions=[],
            )

        mock_get_state.side_effect = mock_state

        mock_list_worktrees.return_value = [
            WorktreeInfo(
                path=tmp_path / "d",
                branch="feature/draft-feature",
                feature_id="draft-feature",
                created_at=datetime.now(),
            ),
            WorktreeInfo(
                path=tmp_path / "a",
                branch="feature/active-feature",
                feature_id="active-feature",
                created_at=datetime.now(),
            ),
            WorktreeInfo(
                path=tmp_path / "m",
                branch="feature/multi-agent",
                feature_id="multi-agent",
                created_at=datetime.now(),
            ),
        ]

        runner = CliRunner()
        result = runner.invoke(feature_list)

        assert result.exit_code == 0
        assert "draft-feature" in result.output
        assert "active-feature" in result.output
        assert "multi-agent" in result.output
        assert "Total: 3" in result.output
        assert "Feature" in result.output  # Table header
        assert "Status" in result.output  # Table header

    @patch("weft.cli.feature.list.get_feature_state")
    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_feature_list_with_feat_prefix(
        self, mock_list_worktrees, mock_settings, mock_get_state, tmp_path: Path
    ):
        """Test features with feat/ prefix are recognized."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
        )

        # Mock feature state
        mock_get_state.return_value = FeatureState(
            feature_name="test",
            status=FeatureStatus.IN_PROGRESS,
            created_at=datetime.now(),
            last_activity=datetime.now(),
            transitions=[],
        )

        mock_list_worktrees.return_value = [
            WorktreeInfo(
                path=tmp_path / "test",
                branch="feat/test",
                feature_id="test",
                created_at=datetime.now(),
            ),
        ]

        runner = CliRunner()
        result = runner.invoke(feature_list)

        assert result.exit_code == 0
        assert "test" in result.output
        assert "feat/test" in result.output
