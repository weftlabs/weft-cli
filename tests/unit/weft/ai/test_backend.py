"""Tests for AI backend abstraction layer."""

from unittest.mock import Mock, patch

import pytest

from weft.ai.backend import (
    AIBackend,
    ClaudeBackend,
    LocalLLMBackend,
    create_backend,
    create_backend_from_config,
)


class TestAIBackend:
    """Tests for AIBackend abstract base class."""

    def test_cannot_instantiate_abstract_class(self) -> None:
        """Test that AIBackend cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            AIBackend()

    def test_must_implement_generate(self) -> None:
        """Test that subclasses must implement generate()."""

        class IncompleteBackend(AIBackend):
            def get_model_info(self):
                return {}

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteBackend()

    def test_must_implement_get_model_info(self) -> None:
        """Test that subclasses must implement get_model_info()."""

        class IncompleteBackend(AIBackend):
            def generate(self, prompt: str) -> str:
                return "test"

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteBackend()


class TestClaudeBackend:
    """Tests for ClaudeBackend implementation."""

    @patch("weft.ai.backend.ClaudeClient")
    def test_initialization_default_model(self, mock_claude_client: Mock) -> None:
        """Test Claude backend initialization with default model."""
        backend = ClaudeBackend(api_key="test-key")

        assert backend.model == "claude-3-5-sonnet-20241022"
        mock_claude_client.assert_called_once_with(
            api_key="test-key", model="claude-3-5-sonnet-20241022"
        )

    @patch("weft.ai.backend.ClaudeClient")
    def test_initialization_custom_model(self, mock_claude_client: Mock) -> None:
        """Test Claude backend initialization with custom model."""
        backend = ClaudeBackend(api_key="test-key", model="claude-3-opus")

        assert backend.model == "claude-3-opus"
        mock_claude_client.assert_called_once_with(api_key="test-key", model="claude-3-opus")

    @patch("weft.ai.backend.ClaudeClient")
    def test_initialization_with_kwargs(self, mock_claude_client: Mock) -> None:
        """Test Claude backend passes kwargs to ClaudeClient."""
        ClaudeBackend(api_key="test-key", model="claude-3-opus", max_tokens=2048, timeout=120)

        mock_claude_client.assert_called_once_with(
            api_key="test-key", model="claude-3-opus", max_tokens=2048, timeout=120
        )

    @patch("weft.ai.backend.ClaudeClient")
    def test_generate_calls_client(self, mock_claude_client: Mock) -> None:
        """Test that generate() calls ClaudeClient.generate()."""
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Generated output"
        mock_claude_client.return_value = mock_client_instance

        backend = ClaudeBackend(api_key="test-key")
        output = backend.generate("Test prompt")

        assert output == "Generated output"
        mock_client_instance.generate.assert_called_once_with("Test prompt", None)

    @patch("weft.ai.backend.ClaudeClient")
    def test_get_model_info(self, mock_claude_client: Mock) -> None:
        """Test get_model_info() returns correct metadata."""
        mock_client_instance = Mock()
        mock_client_instance.max_tokens = 4096
        mock_claude_client.return_value = mock_client_instance

        backend = ClaudeBackend(api_key="test-key", model="claude-3-haiku")
        info = backend.get_model_info()

        assert info["backend"] == "claude"
        assert info["model"] == "claude-3-haiku"
        assert info["max_tokens"] == 4096
        assert info["provider"] == "anthropic"

    @patch("weft.ai.backend.ClaudeClient")
    def test_isinstance_of_aibackend(self, mock_claude_client: Mock) -> None:
        """Test that ClaudeBackend is instance of AIBackend."""
        backend = ClaudeBackend(api_key="test-key")

        assert isinstance(backend, AIBackend)


class TestLocalLLMBackend:
    """Tests for LocalLLMBackend placeholder."""

    def test_initialization(self) -> None:
        """Test local LLM backend initialization."""
        backend = LocalLLMBackend()

        assert isinstance(backend, AIBackend)

    def test_generate_raises_not_implemented(self) -> None:
        """Test that generate() raises NotImplementedError."""
        backend = LocalLLMBackend()

        with pytest.raises(NotImplementedError, match="not yet implemented"):
            backend.generate("test")

        with pytest.raises(NotImplementedError, match="M4 \\(Enterprise Features\\)"):
            backend.generate("test")

    def test_get_model_info(self) -> None:
        """Test get_model_info() returns placeholder data."""
        backend = LocalLLMBackend()
        info = backend.get_model_info()

        assert info["backend"] == "local"
        assert info["model"] == "not-implemented"
        assert info["provider"] == "local"


class TestCreateBackend:
    """Tests for create_backend() factory function."""

    @patch("weft.ai.backend.ClaudeClient")
    def test_create_claude_backend(self, mock_claude_client: Mock) -> None:
        """Test factory creates Claude backend."""
        backend = create_backend("claude", api_key="test-key")

        assert isinstance(backend, ClaudeBackend)

    @patch("weft.ai.backend.ClaudeClient")
    def test_create_claude_with_model(self, mock_claude_client: Mock) -> None:
        """Test factory creates Claude backend with custom model."""
        backend = create_backend("claude", api_key="test-key", model="claude-3-opus")

        assert isinstance(backend, ClaudeBackend)
        assert backend.model == "claude-3-opus"

    def test_create_local_backend(self) -> None:
        """Test factory creates local LLM backend."""
        backend = create_backend("local")

        assert isinstance(backend, LocalLLMBackend)

    def test_create_unknown_backend(self) -> None:
        """Test factory raises error for unknown backend type."""
        with pytest.raises(ValueError, match="Unknown backend type: unknown"):
            create_backend("unknown")

        with pytest.raises(ValueError, match="Supported types: claude, local"):
            create_backend("foobar")


class TestCreateBackendFromConfig:
    """Tests for create_backend_from_config() function."""

    @patch("weft.ai.backend.get_settings")
    @patch("weft.ai.backend.ClaudeClient")
    def test_creates_claude_backend_from_config(
        self, mock_claude_client: Mock, mock_get_settings: Mock
    ) -> None:
        """Test creating Claude backend from configuration."""
        # Create mock settings
        mock_settings = Mock()
        mock_settings.ai_backend = "claude"
        mock_settings.ai_backend_config = {}
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.model = "claude-3-opus"
        mock_get_settings.return_value = mock_settings

        backend = create_backend_from_config()

        assert isinstance(backend, ClaudeBackend)
        assert backend.model == "claude-3-opus"

    @patch("weft.ai.backend.get_settings")
    @patch("weft.ai.backend.ClaudeClient")
    def test_uses_default_claude_when_not_set(
        self, mock_claude_client: Mock, mock_get_settings: Mock
    ) -> None:
        """Test defaults to Claude backend when ai_backend not set."""
        # Create mock settings with ai_backend attribute set to "claude"
        mock_settings = Mock()
        mock_settings.ai_backend = "claude"
        mock_settings.ai_backend_config = {}
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.model = "claude-3-sonnet"

        mock_get_settings.return_value = mock_settings

        backend = create_backend_from_config()

        assert isinstance(backend, ClaudeBackend)
        assert backend.model == "claude-3-sonnet"

    @patch("weft.ai.backend.get_settings")
    @patch("weft.ai.backend.ClaudeClient")
    def test_uses_backend_config_kwargs(
        self, mock_claude_client: Mock, mock_get_settings: Mock
    ) -> None:
        """Test that backend_config kwargs are passed to backend."""
        mock_settings = Mock()
        mock_settings.ai_backend = "claude"
        mock_settings.ai_backend_config = {"max_tokens": 8192, "timeout": 120}
        mock_settings.anthropic_api_key = "test-key"
        mock_settings.model = "claude-3-haiku"
        mock_get_settings.return_value = mock_settings

        create_backend_from_config()

        # Verify ClaudeClient was created with all kwargs
        mock_claude_client.assert_called_once_with(
            api_key="test-key", model="claude-3-haiku", max_tokens=8192, timeout=120
        )

    @patch("weft.ai.backend.get_settings")
    def test_creates_local_backend_from_config(self, mock_get_settings: Mock) -> None:
        """Test creating local backend from configuration."""
        mock_settings = Mock()
        mock_settings.ai_backend = "local"
        mock_settings.ai_backend_config = {}
        mock_get_settings.return_value = mock_settings

        backend = create_backend_from_config()

        assert isinstance(backend, LocalLLMBackend)


class TestIntegration:
    """Integration-style tests."""

    @patch("weft.ai.backend.ClaudeClient")
    def test_end_to_end_claude_backend(self, mock_claude_client: Mock) -> None:
        """Test end-to-end usage of Claude backend."""
        # Setup mock
        mock_client_instance = Mock()
        mock_client_instance.generate.return_value = "Claude's response"
        mock_client_instance.max_tokens = 4096
        mock_claude_client.return_value = mock_client_instance

        # Create backend via factory
        backend = create_backend("claude", api_key="test-key", model="claude-3-opus")

        # Generate output
        output = backend.generate("Design a system")

        # Get model info
        info = backend.get_model_info()

        # Verify
        assert output == "Claude's response"
        assert info["backend"] == "claude"
        assert info["model"] == "claude-3-opus"
        assert isinstance(backend, AIBackend)
