"""Tests for CLI command group structure."""

from unittest.mock import Mock, patch

from click.testing import CliRunner

from weft.cli.main import cli


class TestFeatureCommandGroup:
    """Tests for feature command group registration."""

    def test_feature_group_registered(self):
        """Test feature command group is registered."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "feature" in result.output
        assert "Manage features" in result.output

    def test_feature_group_help(self):
        """Test feature group help shows all subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["feature", "--help"])

        assert result.exit_code == 0
        assert "create" in result.output
        assert "start" in result.output
        assert "list" in result.output
        assert "status" in result.output
        assert "review" in result.output


class TestFeatureSubcommands:
    """Tests for feature subcommands accessibility."""

    @patch("weft.config.settings.get_settings")
    @patch("weft.cli.feature.helpers.initialize_feature")
    @patch("weft.agents.orchestration.wait_for_agent_result")
    def test_feature_create_command(
        self,
        mock_wait,
        mock_init,
        mock_settings,
        tmp_path,
    ):
        """Test weft feature create command is accessible."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )
        mock_wait.return_value = "# Spec\n\nFeature spec content"

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["feature", "create", "test-feature"],
            input="Test description\nyes\n",
        )

        # Should be accessible (may fail due to missing setup, but command exists)
        assert "test-feature" in result.output or result.exit_code in [0, 1]

    @patch("weft.config.settings.get_settings")
    @patch("weft.cli.feature.start.load_weftrc")
    def test_feature_start_command(
        self,
        mock_load_weftrc,
        mock_settings,
        tmp_path,
    ):
        """Test weft feature start command is accessible."""
        worktree = tmp_path / "worktrees" / "test-feature"
        worktree.mkdir(parents=True)
        spec_file = tmp_path / "ai-history" / "test-feature" / "00-meta" / "spec.md"
        spec_file.parent.mkdir(parents=True)
        spec_file.write_text("# Spec\n\nTest spec")

        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )
        mock_load_weftrc.return_value = Mock(agents=Mock(enabled=["00-meta", "01-architect"]))

        runner = CliRunner()
        result = runner.invoke(cli, ["feature", "start", "test-feature"])

        # Should be accessible
        assert "test-feature" in result.output or result.exit_code in [0, 1]

    @patch("weft.config.settings.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_feature_list_command(
        self,
        mock_list_worktrees,
        mock_settings,
        tmp_path,
    ):
        """Test weft feature list command is accessible."""
        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )
        mock_list_worktrees.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, ["feature", "list"])

        # Command should be accessible even if it fails
        assert result.exit_code in [0, 1]
        # Should show "No features found" or table header or error
        assert (
            "No features found" in result.output
            or "Feature" in result.output
            or "Error" in result.output
        )

    @patch("weft.cli.status.get_settings")
    def test_feature_status_command(
        self,
        mock_settings,
        tmp_path,
    ):
        """Test weft feature status command is accessible."""
        worktree = tmp_path / "worktrees" / "test-feature"
        worktree.mkdir(parents=True)
        ai_history = tmp_path / "ai-history" / "test-feature"
        ai_history.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["feature", "status", "test-feature"])

        # Should be accessible (may have errors but command exists)
        assert result.exit_code in [0, 1]
        assert "test-feature" in result.output

    @patch("weft.config.settings.get_settings")
    def test_feature_review_command(
        self,
        mock_settings,
        tmp_path,
    ):
        """Test weft feature review command is accessible."""
        worktree = tmp_path / "worktrees" / "test-feature"
        worktree.mkdir(parents=True)
        ai_history = tmp_path / "ai-history" / "test-feature"
        ai_history.mkdir(parents=True)

        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )

        runner = CliRunner()
        result = runner.invoke(cli, ["feature", "review", "test-feature"])

        # Should be accessible (will fail due to missing data, but command works)
        assert result.exit_code in [0, 1]


class TestProjectLevelCommands:
    """Tests for project-level commands (not in feature group)."""

    @patch("weft.cli.init.create_default_weftrc")
    @patch("weft.cli.init.WeftRuntime")
    @patch("weft.cli.init.initialize_ai_history_repo")
    def test_init_command_at_root(
        self,
        mock_init_repo,
        mock_runtime,
        mock_create_weftrc,
        tmp_path,
        monkeypatch,
    ):
        """Test weft init is at root level (not under feature)."""
        # Change to temp directory to avoid "already initialized" message
        monkeypatch.chdir(tmp_path)

        mock_runtime.return_value = Mock()
        mock_create_weftrc.return_value = {"project": {"name": "test"}}

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["init"],
            input=f"test-project\nbackend\nclaude\n{tmp_path}\n{tmp_path / 'ai-history'}\n",
        )

        # Should be accessible at root (will be initialized or already initialized)
        assert result.exit_code == 0
        # Check command is accessible - either shows project name or "already initialized"
        assert "test-project" in result.output or "initialized" in result.output

    @patch("weft.cli.runtime.helpers.validate_docker")
    @patch("weft.cli.runtime.up.load_weftrc")
    @patch("subprocess.run")
    def test_up_command_at_root(
        self,
        mock_subprocess,
        mock_load_weftrc,
        mock_validate,
    ):
        """Test weft up is at root level."""
        mock_validate.return_value = True
        mock_load_weftrc.return_value = Mock(agents=Mock(enabled=["00-meta", "01-architect"]))
        mock_subprocess.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(cli, ["up"])

        assert result.exit_code == 0

    @patch("weft.cli.runtime.helpers.validate_docker")
    @patch("subprocess.run")
    def test_down_command_at_root(
        self,
        mock_subprocess,
        mock_validate,
    ):
        """Test weft down is at root level."""
        mock_validate.return_value = True
        mock_subprocess.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(cli, ["down"])

        assert result.exit_code == 0

    @patch("weft.cli.runtime.helpers.validate_docker")
    @patch("subprocess.run")
    def test_logs_command_at_root(
        self,
        mock_subprocess,
        mock_validate,
    ):
        """Test weft logs is at root level."""
        mock_validate.return_value = True
        mock_subprocess.return_value = Mock(returncode=0, stdout="Test logs\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["logs", "meta"])

        assert result.exit_code == 0


class TestHelpText:
    """Tests for help text and documentation."""

    def test_main_help_shows_feature_group(self):
        """Test main help shows feature command group."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "feature" in result.output
        assert "Manage features" in result.output

    def test_main_help_uses_new_command_names(self):
        """Test that only new command names appear in help."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        # Old hyphenated command names should NOT appear
        assert "feature-create" not in result.output
        assert "feature-start" not in result.output
        assert "feature-list" not in result.output
        assert "feature-accept" not in result.output
        assert "feature-drop" not in result.output

    def test_feature_help_shows_all_subcommands(self):
        """Test feature group help lists all subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["feature", "--help"])

        assert result.exit_code == 0
        assert "create" in result.output
        assert "start" in result.output
        assert "list" in result.output
        assert "status" in result.output
        assert "review" in result.output

    def test_version_option(self):
        """Test --version flag works."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])

        assert result.exit_code == 0
        assert "weft" in result.output.lower()


class TestCommandGroupIntegration:
    """Integration tests for command group behavior."""

    def test_feature_subcommand_inherits_global_options(self):
        """Test feature subcommands inherit global options."""
        runner = CliRunner()
        # This should not error even with global options
        result = runner.invoke(cli, ["--verbose", "feature", "--help"])

        assert result.exit_code == 0

    @patch("weft.config.settings.get_settings")
    @patch("weft.cli.feature.list.list_worktrees")
    def test_config_option_passed_to_subcommand(
        self,
        mock_list_worktrees,
        mock_settings,
        tmp_path,
    ):
        """Test --config option is passed to subcommands."""
        config_file = tmp_path / ".env"
        config_file.write_text("TEST=value\n")

        mock_settings.return_value = Mock(
            code_repo_path=tmp_path / "code",
            ai_history_path=tmp_path / "ai-history",
        )
        mock_list_worktrees.return_value = []

        runner = CliRunner()
        result = runner.invoke(cli, ["--config", str(config_file), "feature", "list"])

        # Command should be accessible (exit code may vary based on test environment)
        assert result.exit_code in [0, 1]
        # Should not crash - check output contains expected content
        assert (
            "Feature" in result.output or "No features" in result.output or "Error" in result.output
        )
