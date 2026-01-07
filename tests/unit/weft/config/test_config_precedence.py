"""Tests for configuration precedence resolution."""

from unittest.mock import Mock

import pytest

from weft.config.errors import ConfigError
from weft.config.project import AIConfig, ProjectConfig, WeftRC
from weft.config.resolver import ConfigResolver
from weft.config.user import UserConfig, UserDefaults


class TestConfigPrecedence:
    """Test configuration precedence order."""

    def test_cli_overrides_all(self, monkeypatch):
        """Test CLI flags override all other config."""
        resolver = ConfigResolver()
        resolver.cli_args = {"ai.provider": "cli-value"}
        resolver.project_config = Mock(ai=Mock(provider="project-value"))
        resolver.user_config = Mock(defaults=Mock(provider="user-value"))
        monkeypatch.setenv("WEFT_PROVIDER", "env-value")

        result = resolver.resolve("ai.provider")

        assert result == "cli-value"

    def test_project_overrides_user_and_env(self, monkeypatch):
        """Test project config overrides user config and ENV."""
        resolver = ConfigResolver()
        resolver.project_config = Mock(ai=Mock(provider="project-value"))
        resolver.user_config = Mock(defaults=Mock(provider="user-value"))
        monkeypatch.setenv("WEFT_PROVIDER", "env-value")

        result = resolver.resolve("ai.provider")

        assert result == "project-value"

    def test_user_overrides_env(self, monkeypatch):
        """Test user config overrides ENV."""
        resolver = ConfigResolver()
        resolver.user_config = Mock(defaults=Mock(provider="user-value"))
        monkeypatch.setenv("WEFT_PROVIDER", "env-value")

        result = resolver.resolve("defaults.provider")

        assert result == "user-value"

    def test_env_overrides_defaults(self, monkeypatch):
        """Test ENV overrides defaults."""
        resolver = ConfigResolver()
        resolver.defaults = {"ai.provider": "default-value"}
        monkeypatch.setenv("WEFT_AI_PROVIDER", "env-value")

        result = resolver.resolve("ai.provider")

        assert result == "env-value"

    def test_defaults_used_when_nothing_else(self):
        """Test defaults are used when no other config present."""
        resolver = ConfigResolver()
        resolver.defaults = {"ai.provider": "default-value"}

        result = resolver.resolve("ai.provider")

        assert result == "default-value"


class TestSecretResolution:
    """Test secret resolution (secrets only from ENV)."""

    def test_secrets_only_from_env(self, monkeypatch):
        """Test secrets can only come from ENV vars."""
        resolver = ConfigResolver()
        resolver.cli_args = {"api_key": "cli-should-not-work"}
        resolver.project_config = Mock(api_key="project-should-not-work")
        monkeypatch.setenv("WEFT_API_KEY", "sk-correct")

        result = resolver.resolve("api_key", secret=True)

        assert result == "sk-correct"

    def test_secret_not_from_cli(self, monkeypatch):
        """Test secrets are not read from CLI args."""
        resolver = ConfigResolver()
        resolver.cli_args = {"anthropic_api_key": "sk-cli"}
        monkeypatch.delenv("WEFT_ANTHROPIC_API_KEY", raising=False)

        with pytest.raises(ConfigError):
            resolver.resolve("anthropic_api_key", secret=True)

    def test_secret_not_from_project(self, monkeypatch):
        """Test secrets are not read from project config."""
        resolver = ConfigResolver()
        resolver.project_config = Mock(api_key="sk-project")
        monkeypatch.delenv("WEFT_API_KEY", raising=False)

        with pytest.raises(ConfigError):
            resolver.resolve("api_key", secret=True)

    def test_missing_secret_raises_error(self, monkeypatch):
        """Test missing secret raises ConfigError."""
        resolver = ConfigResolver()
        monkeypatch.delenv("WEFT_API_KEY", raising=False)

        with pytest.raises(ConfigError, match="Required secret not found"):
            resolver.resolve("api_key", secret=True)


class TestNestedKeyResolution:
    """Test resolution of nested configuration keys."""

    def test_nested_key_from_project(self):
        """Test resolving nested key from project config."""
        project_config = WeftRC(
            project=ProjectConfig(name="test", type="backend"),
            ai=AIConfig(provider="anthropic", model_profile="quality"),
        )
        resolver = ConfigResolver(project_config=project_config)

        result = resolver.resolve("ai.model_profile")

        assert result == "quality"

    def test_nested_key_from_user(self):
        """Test resolving nested key from user config."""
        user_config = UserConfig(defaults=UserDefaults(provider="openai", log_level="debug"))
        resolver = ConfigResolver(user_config=user_config)

        result = resolver.resolve("defaults.log_level")

        assert result == "debug"

    def test_deeply_nested_key(self):
        """Test resolving deeply nested configuration key."""
        project_config = Mock()
        project_config.git = Mock()
        project_config.git.worktree = Mock(base_branch="develop")

        resolver = ConfigResolver(project_config=project_config)

        result = resolver.resolve("git.worktree.base_branch")

        assert result == "develop"


class TestOptionalResolution:
    """Test optional configuration resolution."""

    def test_resolve_optional_returns_value(self):
        """Test resolve_optional returns value when present."""
        resolver = ConfigResolver()
        resolver.defaults = {"ai.provider": "anthropic"}

        result = resolver.resolve_optional("ai.provider", "default")

        assert result == "anthropic"

    def test_resolve_optional_returns_default(self):
        """Test resolve_optional returns default when not found."""
        resolver = ConfigResolver()

        result = resolver.resolve_optional("nonexistent", "my-default")

        assert result == "my-default"

    def test_resolve_optional_returns_none_by_default(self):
        """Test resolve_optional returns None if no default provided."""
        resolver = ConfigResolver()

        result = resolver.resolve_optional("nonexistent")

        assert result is None


class TestGetAllConfig:
    """Test getting all configuration as dictionary."""

    def test_get_all_config_includes_defaults(self):
        """Test get_all_config includes default values."""
        resolver = ConfigResolver(defaults={"ai.provider": "anthropic", "log_level": "info"})

        config = resolver.get_all_config()

        assert config["ai.provider"] == "anthropic"
        assert config["log_level"] == "info"

    def test_get_all_config_includes_env(self, monkeypatch):
        """Test get_all_config includes environment variables."""
        monkeypatch.setenv("WEFT_PROVIDER", "openai")
        resolver = ConfigResolver()

        config = resolver.get_all_config()

        assert config["provider"] == "openai"

    def test_get_all_config_includes_cli(self):
        """Test get_all_config includes CLI args."""
        resolver = ConfigResolver(cli_args={"provider": "local"})

        config = resolver.get_all_config()

        assert config["provider"] == "local"

    def test_get_all_config_precedence_order(self, monkeypatch):
        """Test get_all_config respects precedence order."""
        monkeypatch.setenv("WEFT_PROVIDER", "env-value")
        resolver = ConfigResolver(
            cli_args={"provider": "cli-value"}, defaults={"provider": "default-value"}
        )

        config = resolver.get_all_config()

        # CLI should win
        assert config["provider"] == "cli-value"


class TestConfigResolverEdgeCases:
    """Test edge cases in configuration resolution."""

    def test_missing_config_raises_error(self):
        """Test missing config key raises ConfigError."""
        resolver = ConfigResolver()

        with pytest.raises(ConfigError, match="Configuration key not found"):
            resolver.resolve("nonexistent.key")

    def test_none_values_skipped(self):
        """Test None values are skipped in precedence."""
        resolver = ConfigResolver()
        resolver.cli_args = {"provider": None}
        resolver.defaults = {"provider": "anthropic"}

        result = resolver.resolve("provider")

        # Should skip None CLI arg and use default
        assert result == "anthropic"

    def test_empty_string_values_not_skipped(self):
        """Test empty string values are not skipped."""
        resolver = ConfigResolver()
        resolver.cli_args = {"log_level": ""}
        resolver.defaults = {"log_level": "info"}

        result = resolver.resolve("log_level")

        # Empty string is valid, should be used
        assert result == ""

    def test_env_var_name_conversion(self, monkeypatch):
        """Test environment variable name conversion."""
        monkeypatch.setenv("WEFT_AI_MODEL_PROFILE", "quality")
        resolver = ConfigResolver()

        result = resolver.resolve("ai.model_profile")

        assert result == "quality"
