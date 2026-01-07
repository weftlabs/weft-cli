"""Tests for .weft/ runtime directory management."""

import pytest

from weft.config.errors import SecurityError
from weft.config.runtime import WeftRuntime


class TestWeftRuntimeInitialization:
    """Test .weft/ directory initialization."""

    def test_weft_directory_created_deterministically(self, tmp_path):
        """Test .weft/ directory structure is created correctly."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        # Check all directories exist
        assert (tmp_path / ".weft").exists()
        assert (tmp_path / ".weft" / "features").exists()
        assert (tmp_path / ".weft" / "tasks" / "in").exists()
        assert (tmp_path / ".weft" / "tasks" / "out").exists()
        assert (tmp_path / ".weft" / "tasks" / "processed").exists()
        assert (tmp_path / ".weft" / "history").exists()
        assert (tmp_path / ".weft" / "history" / "sessions").exists()
        assert (tmp_path / ".weft" / "history" / "prompts").exists()
        assert (tmp_path / ".weft" / "cache").exists()

    def test_agent_directories_created(self, tmp_path):
        """Test agent subdirectories are created."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        agents = ["meta", "architect", "openapi", "ui", "integration", "test"]
        for agent in agents:
            assert (tmp_path / ".weft" / "tasks" / "in" / agent).exists()
            assert (tmp_path / ".weft" / "tasks" / "out" / agent).exists()

    def test_gitignore_created(self, tmp_path):
        """Test .gitignore is created in .weft/."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        gitignore_path = tmp_path / ".weft" / ".gitignore"
        assert gitignore_path.exists()

        content = gitignore_path.read_text()
        assert "*" in content  # Ignore everything
        assert "!.gitignore" in content  # Except the .gitignore itself

    def test_initialization_is_idempotent(self, tmp_path):
        """Test initialize() can be called multiple times safely."""
        runtime = WeftRuntime(tmp_path / ".weft")

        # Call multiple times
        runtime.initialize()
        runtime.initialize()
        runtime.initialize()

        # Should still work correctly
        assert (tmp_path / ".weft").exists()
        assert (tmp_path / ".weft" / "features").exists()


class TestWeftRuntimeSecrets:
    """Test secret detection in .weft/ directory."""

    def test_no_secrets_in_weft_directory(self, tmp_path):
        """Test .weft/ directory does not contain secrets."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        # Write a safe file
        safe_file = tmp_path / ".weft" / "tasks" / "in" / "test.md"
        safe_file.write_text("This is safe content")

        # Should not raise
        runtime.ensure_no_secrets()

    def test_detects_weft_env_variable(self, tmp_path):
        """Test detects WEFT_ environment variable pattern."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        # Write a file with secret
        secret_file = tmp_path / ".weft" / "tasks" / "in" / "test.md"
        secret_file.write_text("WEFT_ANTHROPIC_API_KEY=sk-ant-secret")

        with pytest.raises(SecurityError, match="Potential secret found"):
            runtime.ensure_no_secrets()

    def test_detects_api_key_pattern(self, tmp_path):
        """Test detects API key patterns."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        # Write a file with API key
        secret_file = tmp_path / ".weft" / "tasks" / "in" / "test.md"
        secret_file.write_text("api_key: sk-ant-api03-secret")

        with pytest.raises(SecurityError, match="Potential secret found"):
            runtime.ensure_no_secrets()

    def test_detects_password_field(self, tmp_path):
        """Test detects password field."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        # Write a file with password
        secret_file = tmp_path / ".weft" / "tasks" / "in" / "test.md"
        secret_file.write_text("password: secret123")

        with pytest.raises(SecurityError, match="Potential secret found"):
            runtime.ensure_no_secrets()

    def test_skips_binary_files(self, tmp_path):
        """Test skips binary files during secret scan."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        # Write a binary file with secret pattern
        binary_file = tmp_path / ".weft" / "cache" / "test.bin"
        binary_file.write_bytes(b"\x00\x01\x02WEFT_SECRET")

        # Should not raise (binary files are skipped)
        runtime.ensure_no_secrets()


class TestWeftRuntimeMethods:
    """Test WeftRuntime utility methods."""

    def test_exists_returns_false_initially(self, tmp_path):
        """Test exists() returns False before initialization."""
        runtime = WeftRuntime(tmp_path / ".weft")

        assert runtime.exists() is False

    def test_exists_returns_true_after_init(self, tmp_path):
        """Test exists() returns True after initialization."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        assert runtime.exists() is True

    def test_get_agent_input_dir(self, tmp_path):
        """Test get_agent_input_dir returns correct path."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        input_dir = runtime.get_agent_input_dir("meta")

        assert input_dir == tmp_path / ".weft" / "tasks" / "in" / "meta"
        assert input_dir.exists()

    def test_get_agent_output_dir(self, tmp_path):
        """Test get_agent_output_dir returns correct path."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        output_dir = runtime.get_agent_output_dir("architect")

        assert output_dir == tmp_path / ".weft" / "tasks" / "out" / "architect"
        assert output_dir.exists()

    def test_list_agents(self, tmp_path):
        """Test list_agents returns all configured agents."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        agents = runtime.list_agents()

        assert "meta" in agents
        assert "architect" in agents
        assert "openapi" in agents

    def test_list_agents_empty_before_init(self, tmp_path):
        """Test list_agents returns empty list before initialization."""
        runtime = WeftRuntime(tmp_path / ".weft")

        agents = runtime.list_agents()

        assert agents == []

    def test_clean_cache(self, tmp_path):
        """Test clean_cache removes cached files."""
        runtime = WeftRuntime(tmp_path / ".weft")
        runtime.initialize()

        # Create some cache files
        cache_file1 = runtime.cache / "test1.txt"
        cache_file2 = runtime.cache / "test2.txt"
        cache_file1.write_text("cache content 1")
        cache_file2.write_text("cache content 2")

        # Clean cache
        runtime.clean_cache()

        # Cache files should be removed
        assert not cache_file1.exists()
        assert not cache_file2.exists()
        # But cache directory should still exist
        assert runtime.cache.exists()


class TestWeftRuntimeCustomRoot:
    """Test WeftRuntime with custom root directory."""

    def test_custom_root_directory(self, tmp_path):
        """Test runtime can use custom root directory."""
        custom_root = tmp_path / "custom" / ".weft"
        runtime = WeftRuntime(custom_root)
        runtime.initialize()

        assert custom_root.exists()
        assert (custom_root / "features").exists()
        assert (custom_root / "tasks").exists()

    def test_paths_relative_to_custom_root(self, tmp_path):
        """Test all paths are relative to custom root."""
        custom_root = tmp_path / "custom" / ".weft"
        runtime = WeftRuntime(custom_root)

        assert runtime.features == custom_root / "features"
        assert runtime.tasks_in == custom_root / "tasks" / "in"
        assert runtime.history == custom_root / "history"
