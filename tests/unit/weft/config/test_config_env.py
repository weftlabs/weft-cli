"""Tests for environment variable loading (WEFT_* prefix)."""

import os

import pytest

from weft.config.env import (
    ensure_no_env_in_history,
    get_env_var,
    get_secret,
    load_weft_env_vars,
    validate_required_secrets,
)
from weft.config.errors import ConfigError, SecurityError


class TestLoadWeftEnvVars:
    """Test loading WEFT_* prefixed environment variables."""

    def test_only_weft_prefixed_vars_loaded(self, monkeypatch):
        """Test only WEFT_* environment variables are loaded."""
        monkeypatch.setenv("WEFT_PROVIDER", "anthropic")
        monkeypatch.setenv("CLAUDE_API_KEY", "sk-should-not-load")
        monkeypatch.setenv("API_KEY", "should-not-load")
        monkeypatch.setenv("WEFT_MODEL_PROFILE", "standard")

        vars = load_weft_env_vars()

        assert "PROVIDER" in vars
        assert vars["PROVIDER"] == "anthropic"
        assert "MODEL_PROFILE" in vars
        assert vars["MODEL_PROFILE"] == "standard"
        assert "CLAUDE_API_KEY" not in vars
        assert "API_KEY" not in vars

    def test_weft_prefix_stripped(self, monkeypatch):
        """Test WEFT_ prefix is stripped from keys."""
        monkeypatch.setenv("WEFT_ANTHROPIC_API_KEY", "sk-ant-test")

        vars = load_weft_env_vars()

        assert "ANTHROPIC_API_KEY" in vars
        assert "WEFT_ANTHROPIC_API_KEY" not in vars

    def test_empty_when_no_weft_vars(self, monkeypatch):
        """Test returns empty dict when no WEFT_* vars present."""
        # Clear any WEFT_ vars
        for key in list(os.environ.keys()):
            if key.startswith("WEFT_"):
                monkeypatch.delenv(key, raising=False)

        vars = load_weft_env_vars()

        assert vars == {}


class TestValidateRequiredSecrets:
    """Test validation of required secret environment variables."""

    def test_required_secrets_validation_passes(self, monkeypatch):
        """Test validation passes when required secrets present."""
        monkeypatch.setenv("WEFT_ANTHROPIC_API_KEY", "sk-ant-test")

        # Should not raise
        validate_required_secrets()

    def test_required_secrets_validation_fails(self, monkeypatch):
        """Test validation fails when required secrets missing."""
        # Clear the required secret
        monkeypatch.delenv("WEFT_ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(ConfigError, match="Required environment variables missing"):
            validate_required_secrets()

    def test_error_message_includes_missing_var(self, monkeypatch):
        """Test error message includes the missing variable name."""
        monkeypatch.delenv("WEFT_ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(ConfigError, match="WEFT_ANTHROPIC_API_KEY"):
            validate_required_secrets()


class TestEnsureNoEnvInHistory:
    """Test scanning history for accidentally committed secrets."""

    def test_no_secrets_in_history(self, tmp_path):
        """Test passes when no secrets in history."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        # Create safe file
        safe_file = history_dir / "test.md"
        safe_file.write_text("# Test Document\n\nThis is safe content.")

        # Should not raise
        ensure_no_env_in_history(history_dir)

    def test_detects_weft_env_pattern(self, tmp_path):
        """Test detects WEFT_ pattern in history."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        # Create file with secret
        secret_file = history_dir / "test.md"
        secret_file.write_text("WEFT_ANTHROPIC_API_KEY=sk-ant-secret")

        with pytest.raises(SecurityError, match="Potential secret found"):
            ensure_no_env_in_history(history_dir)

    def test_detects_api_key_pattern(self, tmp_path):
        """Test detects API key patterns in history."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        # Create file with API key
        secret_file = history_dir / "test.md"
        secret_file.write_text("api_key: sk-ant-api03-secret")

        with pytest.raises(SecurityError, match="Potential secret found"):
            ensure_no_env_in_history(history_dir)

    def test_skips_binary_files(self, tmp_path):
        """Test skips binary files during scan."""
        history_dir = tmp_path / "history"
        history_dir.mkdir()

        # Create binary file
        binary_file = history_dir / "test.bin"
        binary_file.write_bytes(b"\x00\x01\x02WEFT_SECRET")

        # Should not raise (binary files are skipped)
        ensure_no_env_in_history(history_dir)

    def test_nonexistent_directory(self, tmp_path):
        """Test handles nonexistent directory gracefully."""
        nonexistent = tmp_path / "does_not_exist"

        # Should not raise
        ensure_no_env_in_history(nonexistent)


class TestGetEnvVar:
    """Test getting individual environment variables."""

    def test_get_env_var_exists(self, monkeypatch):
        """Test getting existing WEFT_* variable."""
        monkeypatch.setenv("WEFT_PROVIDER", "anthropic")

        value = get_env_var("PROVIDER")

        assert value == "anthropic"

    def test_get_env_var_with_default(self, monkeypatch):
        """Test getting variable with default value."""
        monkeypatch.delenv("WEFT_NONEXISTENT", raising=False)

        value = get_env_var("NONEXISTENT", "default_value")

        assert value == "default_value"

    def test_get_env_var_case_insensitive(self, monkeypatch):
        """Test variable name is case-insensitive."""
        monkeypatch.setenv("WEFT_PROVIDER", "anthropic")

        value = get_env_var("provider")

        assert value == "anthropic"


class TestGetSecret:
    """Test getting secrets from environment variables."""

    def test_get_secret_exists(self, monkeypatch):
        """Test getting existing secret."""
        monkeypatch.setenv("WEFT_ANTHROPIC_API_KEY", "sk-ant-test")

        secret = get_secret("ANTHROPIC_API_KEY")

        assert secret == "sk-ant-test"

    def test_get_secret_missing_raises_error(self, monkeypatch):
        """Test missing secret raises ConfigError."""
        monkeypatch.delenv("WEFT_NONEXISTENT", raising=False)

        with pytest.raises(ConfigError, match="Required secret not found"):
            get_secret("NONEXISTENT")

    def test_error_includes_env_var_name(self, monkeypatch):
        """Test error message includes environment variable name."""
        monkeypatch.delenv("WEFT_TEST_SECRET", raising=False)

        with pytest.raises(ConfigError, match="WEFT_TEST_SECRET"):
            get_secret("TEST_SECRET")
