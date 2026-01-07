"""Tests for project initialization command."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from weft.cli.init import copy_prompt_specs, project_init
from weft.config.project import load_weftrc


@pytest.mark.timeout(30)
class TestProjectInitCommand:
    """Tests for project-init CLI command."""

    def test_project_init_with_all_prompts(self, tmp_path: Path, monkeypatch):
        """Test project-init command with all interactive prompts."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            input="my-app\nfullstack\nclaude\n../my-app-ai-history\n",
        )

        assert result.exit_code == 0
        assert "Initializing Weft project: my-app" in result.output
        assert "Created .weftrc.yaml" in result.output
        assert "Created .weft/ directory" in result.output
        assert "Initialized AI history repository" in result.output
        assert "weft up" in result.output  # Next steps

        # Verify .weftrc.yaml was created
        weftrc_path = tmp_path / ".weftrc.yaml"
        assert weftrc_path.exists()

        # Verify .weft/ directory was created
        weft_dir = tmp_path / ".weft"
        assert weft_dir.exists()
        assert (weft_dir / "features").exists()
        assert (weft_dir / "tasks").exists()
        assert (weft_dir / "history").exists()
        assert (weft_dir / "cache").exists()

    def test_project_init_with_cli_options(self, tmp_path: Path, monkeypatch):
        """Test project-init with all options via CLI flags."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test-project",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                "../test-history",
            ],
        )

        assert result.exit_code == 0
        assert "test-project" in result.output
        assert "backend" in result.output

        # Load and verify config
        config = load_weftrc(tmp_path / ".weftrc.yaml")
        assert config is not None
        assert config.project.name == "test-project"
        assert config.project.type == "backend"
        assert config.ai.provider == "anthropic"  # claude maps to anthropic

    def test_project_init_creates_valid_weftrc(self, tmp_path: Path, monkeypatch):
        """Test that created .weftrc.yaml is valid and loadable."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            input="my-app\nfullstack\nclaude\n../history\n",
        )

        assert result.exit_code == 0

        # Load config and verify it's valid
        config = load_weftrc(tmp_path / ".weftrc.yaml")
        assert config is not None
        assert config.project.name == "my-app"
        assert config.project.type == "fullstack"
        assert config.ai.provider == "anthropic"  # claude maps to anthropic
        assert config.ai.history_path == "../history"

    def test_project_init_already_initialized_with_weftrc(self, tmp_path: Path, monkeypatch):
        """Test that init detects existing .weftrc.yaml and exits."""
        monkeypatch.chdir(tmp_path)

        # Create existing .weftrc.yaml
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: existing\n  type: backend\n")

        runner = CliRunner()
        # Use CLI options to avoid prompts (they won't be used anyway since we exit early)
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                "../history",
            ],
        )

        assert result.exit_code == 0
        assert "already initialized" in result.output
        assert "Found existing configuration" in result.output
        assert "weft init --force" in result.output  # Hint about force flag
        assert "weft feature create" in result.output  # Helpful next step hint

    def test_project_init_already_initialized_with_weft_dir(self, tmp_path: Path, monkeypatch):
        """Test that init detects existing .weft/ directory and exits."""
        monkeypatch.chdir(tmp_path)

        # Create existing .weft/ directory (but not .weftrc.yaml)
        weft_dir = tmp_path / ".weft"
        weft_dir.mkdir()
        (weft_dir / "features").mkdir()

        runner = CliRunner()
        # Use CLI options to avoid prompts (they won't be used anyway since we exit early)
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                "../history",
            ],
        )

        assert result.exit_code == 0
        assert "already initialized" in result.output
        assert "Found existing configuration" in result.output
        assert "weft init --force" in result.output  # Hint about force flag
        assert "weft feature create" in result.output  # Helpful next step hint

    def test_project_init_with_ollama_provider(self, tmp_path: Path, monkeypatch):
        """Test project init with Ollama provider uses correct default model."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "ollama",
                "--ai-history-path",
                "../history",
            ],
        )

        assert result.exit_code == 0
        assert "ollama" in result.output

        config = load_weftrc(tmp_path / ".weftrc.yaml")
        assert config.ai.provider == "local"  # ollama maps to local
        assert config.ai.model == "llama2"  # Default for ollama

    def test_project_init_with_custom_model(self, tmp_path: Path, monkeypatch):
        """Test project init with custom model specified."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--model",
                "claude-opus-20240229",
                "--ai-history-path",
                "../history",
            ],
        )

        assert result.exit_code == 0

        config = load_weftrc(tmp_path / ".weftrc.yaml")
        assert config.ai.model == "claude-opus-20240229"

    def test_project_init_existing_ai_history_initializes_git(self, tmp_path: Path, monkeypatch):
        """Test that existing directory is initialized as git repo if not already."""
        monkeypatch.chdir(tmp_path)

        # Create existing AI history directory (but not a git repo)
        history_path = tmp_path / "existing-history"
        history_path.mkdir()

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                str(history_path),
            ],
        )

        assert result.exit_code == 0
        assert "Directory exists but not a git repo, initializing" in result.output
        # Verify it was initialized as git repo
        assert (history_path / ".git").exists()

    def test_project_init_creates_weft_subdirectories(self, tmp_path: Path, monkeypatch):
        """Test that all .weft/ subdirectories are created."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            input="test\nbackend\nclaude\n../history\n",
        )

        assert result.exit_code == 0

        weft_dir = tmp_path / ".weft"
        assert (weft_dir / "features").is_dir()
        assert (weft_dir / "tasks").is_dir()
        assert (weft_dir / "history").is_dir()
        assert (weft_dir / "cache").is_dir()

    def test_project_init_prints_next_steps(self, tmp_path: Path, monkeypatch):
        """Test that next steps are printed."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            input="test\nbackend\nclaude\n../history\n",
        )

        assert result.exit_code == 0
        assert "Next steps:" in result.output
        assert "weft up" in result.output
        assert "weft feature create" in result.output


@pytest.mark.timeout(30)
class TestProjectInitForce:
    """Tests for project re-initialization with --force flag."""

    def test_project_init_force_with_existing_config(self, tmp_path: Path, monkeypatch):
        """Test --force re-initializes existing project."""
        # Mock Path.cwd() to return our test directory
        monkeypatch.setattr("weft.cli.init.Path.cwd", lambda: tmp_path)

        runner = CliRunner()

        # First initialization
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "original",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                str(tmp_path / "history"),
            ],
        )
        assert result.exit_code == 0

        # Re-initialize with --force (change to fullstack and ollama)
        result = runner.invoke(
            project_init,
            [
                "--force",
                "--project-name",
                "updated",
                "--project-type",
                "fullstack",
                "--ai-provider",
                "ollama",
                "--ai-history-path",
                str(tmp_path / "history"),
            ],
        )

        assert result.exit_code == 0
        assert "Re-initializing" in result.output
        assert "Updated .weftrc.yaml" in result.output
        assert "re-initialized successfully" in result.output

        # Verify config was updated
        config = load_weftrc(tmp_path / ".weftrc.yaml")
        assert config.project.name == "updated"
        assert config.project.type == "fullstack"
        assert config.ai.provider == "local"  # ollama maps to local
        assert config.ai.model == "llama2"  # Default for ollama

    def test_project_init_force_uses_existing_config_as_defaults(self, tmp_path: Path, monkeypatch):
        """Test --force uses existing config values as defaults in prompts."""
        monkeypatch.chdir(tmp_path)
        # Mock Path.cwd() to return our test directory
        monkeypatch.setattr("weft.cli.init.Path.cwd", lambda: tmp_path)

        runner = CliRunner()

        # First initialization
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "my-app",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--model",
                "claude-opus-20240229",
                "--ai-history-path",
                str(tmp_path / "weft-ai-history"),
            ],
        )
        assert result.exit_code == 0

        # Re-initialize with --force, using prompts (press Enter to accept defaults)
        result = runner.invoke(
            project_init,
            ["--force"],
            input="\n\n\n\n\n",  # Accept all defaults
        )

        assert result.exit_code == 0
        assert "Re-initializing" in result.output
        assert "Current configuration will be used as defaults" in result.output

        # Verify config preserved
        config = load_weftrc(tmp_path / ".weftrc.yaml")
        assert config.project.name == "my-app"
        assert config.project.type == "backend"
        assert config.ai.provider == "anthropic"
        assert config.ai.model == "claude-opus-20240229"

    def test_project_init_force_provider_mapping_reverse(self, tmp_path: Path, monkeypatch):
        """Test --force correctly maps internal provider back to user-friendly name."""
        monkeypatch.chdir(tmp_path)
        # Mock Path.cwd() to return our test directory
        monkeypatch.setattr("weft.cli.init.Path.cwd", lambda: tmp_path)

        runner = CliRunner()

        # First initialization creates anthropic provider
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                str(tmp_path / "history"),
            ],
        )
        assert result.exit_code == 0

        config = load_weftrc(tmp_path / ".weftrc.yaml")
        assert config.ai.provider == "anthropic"  # Internal name

        # Re-init with --force should show "claude" as default, not "anthropic"
        result = runner.invoke(
            project_init,
            ["--force"],
            input="\n\n\n\n\n",  # Accept all defaults (including model)
        )

        assert result.exit_code == 0
        # The output should show claude as the provider (user-friendly name)
        assert "claude" in result.output.lower()

    def test_project_init_force_updates_next_steps_message(self, tmp_path: Path, monkeypatch):
        """Test --force shows different next steps than initial init."""
        monkeypatch.chdir(tmp_path)
        # Mock Path.cwd() to return our test directory
        monkeypatch.setattr("weft.cli.init.Path.cwd", lambda: tmp_path)

        runner = CliRunner()

        # First initialization
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                str(tmp_path / "history"),
            ],
        )
        assert result.exit_code == 0
        assert "Run 'weft up' to start the docker runtime" in result.output

        # Re-initialize with --force
        result = runner.invoke(
            project_init,
            [
                "--force",
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                str(tmp_path / "history"),
            ],
        )

        assert result.exit_code == 0
        assert "Review updated .weftrc.yaml" in result.output
        assert "Restart runtime if running" in result.output
        assert "weft down && weft up" in result.output

    def test_project_init_force_preserves_weft_directory(self, tmp_path: Path, monkeypatch):
        """Test --force preserves existing .weft/ directory and contents."""
        monkeypatch.chdir(tmp_path)
        # Mock Path.cwd() to return our test directory
        monkeypatch.setattr("weft.cli.init.Path.cwd", lambda: tmp_path)

        runner = CliRunner()

        # First initialization
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                str(tmp_path / "history"),
            ],
        )
        assert result.exit_code == 0

        # Add a custom file to .weft/
        custom_file = tmp_path / ".weft" / "features" / "custom.txt"
        custom_file.write_text("custom data")

        # Re-initialize with --force
        result = runner.invoke(
            project_init,
            [
                "--force",
                "--project-name",
                "test-updated",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                str(tmp_path / "history"),
            ],
        )

        assert result.exit_code == 0
        assert "Verifying .weft/ directory" in result.output

        # Verify custom file still exists
        assert custom_file.exists()
        assert custom_file.read_text() == "custom data"

    def test_project_init_force_initializes_ai_history_if_missing(
        self, tmp_path: Path, monkeypatch
    ):
        """Test --force initializes AI history if directory exists but isn't a git repo."""
        monkeypatch.chdir(tmp_path)
        # Mock Path.cwd() to return our test directory
        monkeypatch.setattr("weft.cli.init.Path.cwd", lambda: tmp_path)

        runner = CliRunner()

        # First initialization
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                str(tmp_path / "ai-history"),
            ],
        )
        assert result.exit_code == 0

        # Delete .git directory from AI history
        import shutil

        ai_history_git = tmp_path / "ai-history" / ".git"
        if ai_history_git.exists():
            shutil.rmtree(ai_history_git)

        # Re-initialize with --force
        result = runner.invoke(
            project_init,
            [
                "--force",
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                str(tmp_path / "ai-history"),
            ],
        )

        assert result.exit_code == 0
        assert "Directory exists but not a git repo, initializing" in result.output
        assert ai_history_git.exists()


@pytest.mark.timeout(30)
class TestProjectInitIntegration:
    """Integration tests for project initialization."""

    def test_full_project_initialization_workflow(self, tmp_path: Path, monkeypatch):
        """Test complete workflow from init to loading config."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()

        # Initialize project
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "integration-test",
                "--project-type",
                "fullstack",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                "../integration-history",
            ],
        )

        assert result.exit_code == 0

        # Verify all artifacts created
        assert (tmp_path / ".weftrc.yaml").exists()
        assert (tmp_path / ".weft").is_dir()
        assert (tmp_path / ".weft" / "features").is_dir()

        # Load and verify config is valid
        config = load_weftrc()
        assert config.project.name == "integration-test"
        assert config.project.type == "fullstack"
        assert config.ai.provider == "anthropic"  # claude maps to anthropic

        # Verify agents are configured with defaults
        assert "meta" in config.agents.enabled
        assert "architect" in config.agents.enabled


@pytest.mark.timeout(30)
class TestCopyPromptSpecs:
    """Tests for copy_prompt_specs function."""

    def test_copy_prompt_specs_success(self, tmp_path: Path):
        """Test copying prompt specs to destination directory."""
        dest_dir = tmp_path / "prompts"

        copy_prompt_specs(dest_dir)

        # Verify versioned directory created
        version_dir = dest_dir / "v1.0.0"
        assert version_dir.exists()

        # Verify all spec files copied
        expected_files = [
            "00_meta.md",
            "01_architect.md",
            "02-openapi.md",
            "03-ui.md",
            "04-integration.md",
            "05-test.md",
        ]

        for filename in expected_files:
            spec_file = version_dir / filename
            assert spec_file.exists(), f"Expected {filename} to be copied"
            assert spec_file.stat().st_size > 0, f"Expected {filename} to have content"

    def test_copy_prompt_specs_missing_source(self, tmp_path: Path):
        """Test error when source directory doesn't exist."""
        dest_dir = tmp_path / "prompts"

        # Mock the source directory path to point to non-existent location
        with patch("weft.cli.init.Path") as mock_path:
            # Make Path(...).parent.parent / "prompt-specs" point to non-existent directory
            mock_file = Mock()
            mock_file.parent.parent = tmp_path / "non-existent"
            mock_path.return_value = dest_dir
            mock_path.__file__ = mock_file

            with pytest.raises(FileNotFoundError, match="Agents directory not found"):
                copy_prompt_specs(dest_dir)

    def test_project_init_copies_prompt_specs(self, tmp_path: Path, monkeypatch):
        """Test that project init copies prompt specs and shows them in output."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            [
                "--project-name",
                "test",
                "--project-type",
                "backend",
                "--ai-provider",
                "claude",
                "--ai-history-path",
                "../history",
            ],
        )

        assert result.exit_code == 0
        assert "Copying agent prompt specifications" in result.output
        assert "Copied prompt specs to .weft/prompts/v1.0.0/" in result.output
        assert "00_meta.md" in result.output
        assert "01_architect.md" in result.output
        assert "Edit .weft/prompts/v1.0.0/*.md to customize agent behavior" in result.output

        # Verify specs were actually copied
        prompts_dir = tmp_path / ".weft" / "prompts" / "v1.0.0"
        assert prompts_dir.exists()
        assert (prompts_dir / "00_meta.md").exists()
        assert (prompts_dir / "01_architect.md").exists()

    def test_project_init_prompt_spec_copy_failure_shows_warning(self, tmp_path: Path, monkeypatch):
        """Test that init shows warning but continues when spec copying fails."""
        monkeypatch.chdir(tmp_path)

        # Mock copy_prompt_specs to raise an exception
        with patch("weft.cli.init.copy_prompt_specs") as mock_copy:
            mock_copy.side_effect = Exception("Source not found")

            runner = CliRunner()
            result = runner.invoke(
                project_init,
                [
                    "--project-name",
                    "test",
                    "--project-type",
                    "backend",
                    "--ai-provider",
                    "claude",
                    "--ai-history-path",
                    "../history",
                ],
            )

            assert result.exit_code == 0  # Should still succeed
            assert "Warning: Could not copy prompt specs" in result.output
            assert "Agents will use default specifications" in result.output
            assert "Initializing AI history repository" in result.output  # Should continue

    def test_project_init_creates_prompts_directory(self, tmp_path: Path, monkeypatch):
        """Test that init creates prompts directory in .weft structure."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            input="test\nbackend\nclaude\n../history\n",
        )

        assert result.exit_code == 0

        # Verify prompts directory exists
        weft_dir = tmp_path / ".weft"
        assert (weft_dir / "prompts").is_dir()

        # Verify it's shown in output
        assert "prompts/" in result.output


@pytest.mark.timeout(30)
class TestGitignoreUpdate:
    """Tests for .gitignore update functionality."""

    def test_project_init_creates_gitignore(self, tmp_path: Path, monkeypatch):
        """Test project-init creates .gitignore with weft directories."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            input="test\nbackend\nclaude\n../history\n",
        )

        assert result.exit_code == 0
        assert "Updated .gitignore" in result.output

        # Verify .gitignore was created
        gitignore_path = tmp_path / ".gitignore"
        assert gitignore_path.exists()

        gitignore_content = gitignore_path.read_text()
        assert ".weft/" in gitignore_content
        assert "worktrees/" in gitignore_content
        assert "# Weft AI workflow directories" in gitignore_content

    def test_project_init_updates_existing_gitignore(self, tmp_path: Path, monkeypatch):
        """Test project-init appends to existing .gitignore."""
        monkeypatch.chdir(tmp_path)

        # Create existing .gitignore
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("node_modules/\n*.pyc\n")

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            input="test\nbackend\nclaude\n../history\n",
        )

        assert result.exit_code == 0
        assert "Updated .gitignore" in result.output

        # Verify .gitignore was updated
        gitignore_content = gitignore_path.read_text()
        assert "node_modules/" in gitignore_content
        assert "*.pyc" in gitignore_content
        assert ".weft/" in gitignore_content
        assert "worktrees/" in gitignore_content
        assert "# Weft AI workflow directories" in gitignore_content

    def test_project_init_skips_duplicate_entries(self, tmp_path: Path, monkeypatch):
        """Test project-init doesn't add duplicate entries to .gitignore."""
        monkeypatch.chdir(tmp_path)

        # Create existing .gitignore with our entries
        gitignore_path = tmp_path / ".gitignore"
        gitignore_path.write_text("node_modules/\n.weft/\nworktrees/\n")

        runner = CliRunner()
        result = runner.invoke(
            project_init,
            input="test\nbackend\nclaude\n../history\n",
        )

        assert result.exit_code == 0

        # Verify .gitignore wasn't duplicated
        gitignore_content = gitignore_path.read_text()
        assert gitignore_content.count(".weft/") == 1
        assert gitignore_content.count("worktrees/") == 1
        # Comment should not be added if no new entries
        assert "# Weft AI workflow directories" not in gitignore_content
