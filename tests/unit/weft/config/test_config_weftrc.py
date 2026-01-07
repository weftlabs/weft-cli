"""Tests for .weftrc.yaml project configuration."""

import pytest

from weft.config.errors import ConfigError
from weft.config.project import (
    ProjectConfig,
    WeftRC,
    contains_secrets,
    create_default_weftrc,
    load_weftrc,
    validate_weftrc,
)


class TestLoadWeftrc:
    """Test loading .weftrc.yaml files."""

    def test_load_valid_weftrc(self, tmp_path):
        """Test loading valid .weftrc.yaml."""
        weftrc_path = tmp_path / ".weftrc.yaml"
        weftrc_path.write_text(
            """
project:
  name: test-project
  type: backend
ai:
  provider: anthropic
  model_profile: standard
"""
        )

        config = load_weftrc(weftrc_path)

        assert config is not None
        assert config.project.name == "test-project"
        assert config.project.type == "backend"
        assert config.ai.provider == "anthropic"
        assert config.ai.model_profile == "standard"

    def test_load_nonexistent_returns_none(self, tmp_path):
        """Test loading nonexistent file returns None."""
        weftrc_path = tmp_path / ".weftrc.yaml"

        config = load_weftrc(weftrc_path)

        assert config is None

    def test_invalid_yaml_fails_fast(self, tmp_path):
        """Test invalid YAML fails with clear error."""
        weftrc_path = tmp_path / ".weftrc.yaml"
        weftrc_path.write_text("invalid: yaml: content:")

        with pytest.raises(ConfigError, match="Invalid YAML"):
            load_weftrc(weftrc_path)

    def test_missing_required_fields(self, tmp_path):
        """Test .weftrc.yaml missing required fields."""
        weftrc_path = tmp_path / ".weftrc.yaml"
        weftrc_path.write_text(
            """
ai:
  provider: anthropic
# Missing: project section
"""
        )

        with pytest.raises(ConfigError):
            load_weftrc(weftrc_path)

    def test_defaults_applied(self, tmp_path):
        """Test default values are applied."""
        weftrc_path = tmp_path / ".weftrc.yaml"
        weftrc_path.write_text(
            """
project:
  name: test-project
  type: backend
# ai section omitted - should use defaults
"""
        )

        config = load_weftrc(weftrc_path)

        assert config.ai.provider == "anthropic"
        assert config.ai.model_profile == "standard"


class TestSecretsDetection:
    """Test detection of secrets in .weftrc.yaml."""

    def test_secrets_in_weftrc_rejected(self, tmp_path):
        """Test .weftrc.yaml with secrets is rejected."""
        weftrc_path = tmp_path / ".weftrc.yaml"
        weftrc_path.write_text(
            """
project:
  name: test
  type: backend
ai:
  api_key: sk-ant-api03-secret  # This should fail
"""
        )

        with pytest.raises(ConfigError, match="Secrets detected"):
            load_weftrc(weftrc_path)

    def test_contains_secrets_detects_api_key(self):
        """Test contains_secrets detects api_key field."""
        data = {"project": {"name": "test"}, "ai": {"api_key": "secret"}}

        assert contains_secrets(data) is True

    def test_contains_secrets_detects_password(self):
        """Test contains_secrets detects password field."""
        data = {"project": {"name": "test"}, "database": {"password": "secret123"}}

        assert contains_secrets(data) is True

    def test_contains_secrets_detects_token(self):
        """Test contains_secrets detects token field."""
        data = {"project": {"name": "test"}, "github": {"token": "ghp_secret"}}

        assert contains_secrets(data) is True

    def test_contains_secrets_detects_sk_prefix(self):
        """Test contains_secrets detects sk- prefix (API keys)."""
        data = {"project": {"name": "test"}, "credentials": "sk-ant-api03-secret"}

        assert contains_secrets(data) is True

    def test_contains_secrets_safe_content(self):
        """Test contains_secrets returns False for safe content."""
        data = {
            "project": {"name": "test", "type": "backend"},
            "ai": {"provider": "anthropic"},
            "agents": {"enabled": ["meta", "architect"]},
        }

        assert contains_secrets(data) is False


class TestValidateWeftrc:
    """Test validation of .weftrc.yaml configuration."""

    def test_invalid_project_type(self):
        """Test invalid project type is rejected."""
        config = WeftRC(project=ProjectConfig(name="test", type="invalid_type"))

        with pytest.raises(ConfigError, match="Invalid project.type"):
            validate_weftrc(config)

    def test_valid_project_types(self):
        """Test all valid project types are accepted."""
        for project_type in ["backend", "frontend", "fullstack"]:
            config = WeftRC(project=ProjectConfig(name="test", type=project_type))
            # Should not raise
            validate_weftrc(config)

    def test_invalid_ai_provider(self):
        """Test invalid AI provider is rejected."""
        config = WeftRC(project=ProjectConfig(name="test", type="backend"))
        config.ai.provider = "invalid_provider"

        with pytest.raises(ConfigError, match="Invalid ai.provider"):
            validate_weftrc(config)

    def test_valid_ai_providers(self):
        """Test all valid AI providers are accepted."""
        for provider in ["anthropic", "openai", "local"]:
            config = WeftRC(project=ProjectConfig(name="test", type="backend"))
            config.ai.provider = provider
            # Should not raise
            validate_weftrc(config)

    def test_invalid_model_profile(self):
        """Test invalid model profile is rejected."""
        config = WeftRC(project=ProjectConfig(name="test", type="backend"))
        config.ai.model_profile = "invalid_profile"

        with pytest.raises(ConfigError, match="Invalid ai.model_profile"):
            validate_weftrc(config)

    def test_valid_model_profiles(self):
        """Test all valid model profiles are accepted."""
        for profile in ["fast", "standard", "quality"]:
            config = WeftRC(project=ProjectConfig(name="test", type="backend"))
            config.ai.model_profile = profile
            # Should not raise
            validate_weftrc(config)

    def test_invalid_agent_names(self):
        """Test invalid agent names are rejected."""
        config = WeftRC(project=ProjectConfig(name="test", type="backend"))
        config.agents.enabled = ["meta", "invalid_agent"]

        with pytest.raises(ConfigError, match="Invalid agents in enabled list"):
            validate_weftrc(config)

    def test_valid_agent_names(self):
        """Test all valid agent names are accepted."""
        config = WeftRC(project=ProjectConfig(name="test", type="backend"))
        config.agents.enabled = ["meta", "architect", "openapi", "ui", "integration", "test"]
        # Should not raise
        validate_weftrc(config)


class TestCreateDefaultWeftrc:
    """Test creating default .weftrc.yaml files."""

    def test_creates_default_config(self, tmp_path):
        """Test creates default configuration."""
        config = create_default_weftrc(tmp_path)

        assert config.project.name == "my-project"
        assert config.project.type == "backend"
        assert (tmp_path / ".weftrc.yaml").exists()

    def test_file_is_valid_yaml(self, tmp_path):
        """Test created file is valid YAML."""
        create_default_weftrc(tmp_path)

        # Should be able to load it back
        weftrc_path = tmp_path / ".weftrc.yaml"
        config = load_weftrc(weftrc_path)
        assert config is not None

    def test_default_values(self, tmp_path):
        """Test default configuration has expected values."""
        config = create_default_weftrc(tmp_path)

        assert config.ai.provider == "anthropic"
        assert config.ai.model_profile == "standard"
        assert "meta" in config.agents.enabled
        assert "architect" in config.agents.enabled
