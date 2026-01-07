"""Tests for configuration settings management."""

from pathlib import Path

import pytest

from weft.config.settings import (
    Settings,
    get_settings,
    load_settings,
    reset_settings,
)


@pytest.fixture(autouse=True)
def reset_settings_singleton():
    """Reset settings singleton before each test."""
    reset_settings()
    yield
    reset_settings()


class TestSettings:
    """Tests for Settings class."""

    def test_settings_initialization(self, temp_dir: Path) -> None:
        """Test Settings initialization with all parameters."""
        code_repo = temp_dir / "code"
        code_repo.mkdir()
        ai_history = temp_dir / "history"

        settings = Settings(
            code_repo_path=code_repo,
            ai_history_path=ai_history,
            anthropic_api_key="test-key",
            model="claude-3-opus",
            poll_interval=5,
            log_level="DEBUG",
        )

        assert settings.code_repo_path == code_repo
        assert settings.ai_history_path == ai_history
        assert settings.anthropic_api_key == "test-key"
        assert settings.model == "claude-3-opus"
        assert settings.poll_interval == 5
        assert settings.log_level == "DEBUG"

    def test_settings_defaults(self, temp_dir: Path) -> None:
        """Test Settings uses default values correctly."""
        code_repo = temp_dir / "code"
        code_repo.mkdir()

        settings = Settings(
            code_repo_path=code_repo,
            ai_history_path=temp_dir / "history",
            anthropic_api_key="test-key",
        )

        assert settings.model == "claude-3-5-sonnet-20241022"
        assert settings.poll_interval == 2
        assert settings.log_level == "INFO"


class TestLoadSettings:
    """Tests for load_settings function."""

    def test_load_settings_from_env(self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading settings from environment variables."""
        code_repo = temp_dir / "code"
        code_repo.mkdir()
        ai_history = temp_dir / "history"

        monkeypatch.setenv("WEFT_CODE_REPO_PATH", str(code_repo))
        monkeypatch.setenv("WEFT_AI_HISTORY_PATH", str(ai_history))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        settings = load_settings()

        assert settings.code_repo_path == code_repo
        assert settings.ai_history_path == ai_history
        assert settings.anthropic_api_key == "test-key"
        assert settings.model == "claude-3-5-sonnet-20241022"
        assert settings.poll_interval == 2

    def test_load_settings_custom_values(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test loading settings with custom values."""
        code_repo = temp_dir / "code"
        code_repo.mkdir()

        monkeypatch.setenv("WEFT_CODE_REPO_PATH", str(code_repo))
        monkeypatch.setenv("WEFT_AI_HISTORY_PATH", str(temp_dir / "history"))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "custom-key")
        monkeypatch.setenv("WEFT_MODEL", "claude-3-opus")
        monkeypatch.setenv("WEFT_POLL_INTERVAL", "10")
        monkeypatch.setenv("WEFT_LOG_LEVEL", "DEBUG")

        settings = load_settings()

        assert settings.anthropic_api_key == "custom-key"
        assert settings.model == "claude-3-opus"
        assert settings.poll_interval == 10
        assert settings.log_level == "DEBUG"

    def test_load_settings_expanduser(
        self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that paths with ~ are expanded."""
        # Create a test directory in user's home
        home = Path.home()
        code_repo = home / "test-code"
        code_repo.mkdir(exist_ok=True)

        try:
            monkeypatch.setenv("WEFT_CODE_REPO_PATH", "~/test-code")
            monkeypatch.setenv("WEFT_AI_HISTORY_PATH", "~/test-history")
            monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

            settings = load_settings()

            # Path should be expanded
            assert settings.code_repo_path == code_repo
            assert str(settings.ai_history_path).startswith(str(home))
        finally:
            # Cleanup
            if code_repo.exists():
                code_repo.rmdir()


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_settings_workflow(self, temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test complete settings workflow."""
        code_repo = temp_dir / "code"
        code_repo.mkdir()

        # Set environment
        monkeypatch.setenv("WEFT_CODE_REPO_PATH", str(code_repo))
        monkeypatch.setenv("WEFT_AI_HISTORY_PATH", str(temp_dir / "history"))
        monkeypatch.setenv("ANTHROPIC_API_KEY", "my-api-key")
        monkeypatch.setenv("WEFT_MODEL", "claude-3-opus")
        monkeypatch.setenv("WEFT_POLL_INTERVAL", "3")
        monkeypatch.setenv("WEFT_LOG_LEVEL", "DEBUG")

        # Load settings
        settings = load_settings()

        # Verify all values
        assert settings.code_repo_path == code_repo
        assert settings.anthropic_api_key == "my-api-key"
        assert settings.model == "claude-3-opus"
        assert settings.poll_interval == 3
        assert settings.log_level == "DEBUG"

        # Verify get_settings works
        retrieved = get_settings()
        assert retrieved.anthropic_api_key == "my-api-key"
        assert retrieved.model == "claude-3-opus"
