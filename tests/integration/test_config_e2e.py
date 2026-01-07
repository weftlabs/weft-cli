"""End-to-end integration tests for configuration system."""

import os
from pathlib import Path

import pytest

from weft.config import (
    WeftRuntime,
    create_default_weftrc,
    load_config,
    load_weftrc,
)
from weft.config.errors import ConfigError


class TestConfigurationE2E:
    """End-to-end configuration loading tests."""

    def test_full_config_resolution(self, tmp_path, monkeypatch):
        """Test complete config resolution with all sources."""
        # Setup project directory
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Create .weftrc.yaml
        weftrc = project_dir / ".weftrc.yaml"
        weftrc.write_text(
            """
project:
  name: test-project
  type: backend
ai:
  provider: anthropic
  model_profile: standard
"""
        )

        # Create user config
        user_config_dir = tmp_path / "config" / "weft"
        user_config_dir.mkdir(parents=True)
        user_config = user_config_dir / "config.yaml"
        user_config.write_text(
            """
defaults:
  log_level: debug
"""
        )
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))

        # Set ENV vars
        monkeypatch.setenv("WEFT_ANTHROPIC_API_KEY", "sk-test")
        monkeypatch.setenv("WEFT_LOG_LEVEL", "info")  # Lower priority than user config

        # Load config
        project_config, user_cfg, resolver = load_config(
            project_path=str(project_dir),
            cli_args={"ai.model_profile": "quality"},  # Should override project config
        )

        # Test project config loaded
        assert project_config is not None
        assert project_config.project.name == "test-project"

        # Test user config loaded
        assert user_cfg is not None

        # Test resolution with precedence
        model_profile = resolver.resolve("ai.model_profile")
        assert model_profile == "quality"  # CLI wins

        provider = resolver.resolve("ai.provider")
        assert provider == "anthropic"  # From project config

        log_level = resolver.resolve("defaults.log_level")
        assert log_level == "debug"  # User config wins over ENV

    def test_project_without_weftrc(self, tmp_path, monkeypatch):
        """Test project without .weftrc.yaml uses defaults."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # No .weftrc.yaml file

        project_config, user_cfg, resolver = load_config(project_path=str(project_dir))

        # Project config should be None
        assert project_config is None

        # But resolver should still work with defaults
        provider = resolver.resolve("ai.provider")
        assert provider == "anthropic"  # Default value

    def test_minimal_setup(self, tmp_path, monkeypatch):
        """Test minimal setup with only required ENV vars."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Only set required secret
        monkeypatch.setenv("WEFT_ANTHROPIC_API_KEY", "sk-test")

        # Clear all other WEFT_ vars
        for key in list(os.environ.keys()):
            if key.startswith("WEFT_") and key != "WEFT_ANTHROPIC_API_KEY":
                monkeypatch.delenv(key, raising=False)

        # Should work with just defaults
        project_config, user_cfg, resolver = load_config(project_path=str(project_dir))

        # Can resolve default values
        provider = resolver.resolve("ai.provider")
        assert provider == "anthropic"


class TestWeftRuntimeE2E:
    """End-to-end tests for runtime directory."""

    def test_initialize_and_use_runtime(self, tmp_path, monkeypatch):
        """Test initializing and using .weft/ runtime directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Create .weftrc.yaml
        create_default_weftrc(project_dir)

        # Initialize runtime
        runtime = WeftRuntime()
        runtime.initialize()

        # Check structure created
        assert (project_dir / ".weft").exists()
        assert runtime.exists()

        # Test agent directories
        meta_input = runtime.get_agent_input_dir("meta")
        assert meta_input.exists()

        # Write a task
        task_file = meta_input / "test_task.md"
        task_file.write_text("# Test Task\n\nCreate a feature...")

        # Verify no secrets
        runtime.ensure_no_secrets()  # Should not raise

    def test_runtime_with_project_config(self, tmp_path, monkeypatch):
        """Test runtime directory uses project config paths."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Create .weftrc.yaml with custom paths
        weftrc = project_dir / ".weftrc.yaml"
        weftrc.write_text(
            """
project:
  name: test-project
  type: backend
paths:
  root: .weft
  features: .weft/features
  tasks: .weft/tasks
  history: .weft/history
"""
        )

        # Load config
        project_config = load_weftrc(weftrc)
        assert project_config is not None

        # Initialize runtime with config paths
        runtime = WeftRuntime(Path(project_config.paths.root))
        runtime.initialize()

        # Verify paths match config
        assert runtime.root == Path(".weft")
        assert runtime.features == Path(".weft/features")


class TestConfigurationLifecycle:
    """Test complete configuration lifecycle."""

    def test_create_project_and_configure(self, tmp_path, monkeypatch):
        """Test creating a new project and configuring it."""
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Step 1: Create default .weftrc.yaml
        _ = create_default_weftrc(project_dir)
        weftrc = project_dir / ".weftrc.yaml"
        assert weftrc.exists()

        # Step 2: Initialize runtime
        runtime = WeftRuntime()
        runtime.initialize()
        assert runtime.exists()

        # Step 3: Set up environment
        monkeypatch.setenv("WEFT_ANTHROPIC_API_KEY", "sk-test-key")

        # Step 4: Load and use configuration
        project_config, user_cfg, resolver = load_config(project_path=str(project_dir))

        # Verify everything works
        assert project_config is not None
        assert resolver.resolve("ai.provider") == "anthropic"

        # Step 5: Get secret from ENV
        api_key = resolver.resolve("anthropic_api_key", secret=True)
        assert api_key == "sk-test-key"

    def test_project_migration_scenario(self, tmp_path, monkeypatch):
        """Test migrating from no config to full config."""
        project_dir = tmp_path / "existing-project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Initial state: no configuration
        runtime = WeftRuntime()
        assert not runtime.exists()

        # Add configuration
        weftrc = project_dir / ".weftrc.yaml"
        weftrc.write_text(
            """
project:
  name: existing-project
  type: fullstack
ai:
  provider: anthropic
agents:
  enabled:
    - meta
    - architect
    - ui
"""
        )

        # Initialize runtime
        runtime.initialize()

        # Load config
        project_config = load_weftrc(weftrc)
        assert project_config.project.name == "existing-project"
        assert project_config.project.type == "fullstack"
        assert "ui" in project_config.agents.enabled


class TestErrorHandling:
    """Test error handling in configuration system."""

    def test_invalid_weftrc_provides_clear_error(self, tmp_path, monkeypatch):
        """Test invalid .weftrc.yaml provides clear error message."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Create invalid .weftrc.yaml
        weftrc = project_dir / ".weftrc.yaml"
        weftrc.write_text(
            """
project:
  name: test
  type: invalid-type
"""
        )

        with pytest.raises(ConfigError, match="Invalid project.type"):
            load_weftrc(weftrc)

    def test_secrets_in_weftrc_blocked(self, tmp_path, monkeypatch):
        """Test secrets in .weftrc.yaml are blocked."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Create .weftrc.yaml with secret
        weftrc = project_dir / ".weftrc.yaml"
        weftrc.write_text(
            """
project:
  name: test
  type: backend
ai:
  api_key: sk-ant-secret
"""
        )

        with pytest.raises(ConfigError, match="Secrets detected"):
            load_weftrc(weftrc)

    def test_missing_secret_provides_clear_error(self, tmp_path, monkeypatch):
        """Test missing secret provides clear error message."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)

        # Clear secret
        monkeypatch.delenv("WEFT_ANTHROPIC_API_KEY", raising=False)

        project_config, user_cfg, resolver = load_config(project_path=str(project_dir))

        with pytest.raises(ConfigError, match="WEFT_ANTHROPIC_API_KEY"):
            resolver.resolve("anthropic_api_key", secret=True)
