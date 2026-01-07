"""Tests for ClaudeClient."""

import logging
from unittest.mock import Mock, patch

import pytest
from anthropic import APIError, APITimeoutError, RateLimitError

from weft.ai.claude_client import ClaudeClient


def create_mock_response(status_code: int) -> Mock:
    """Create a mock HTTP response for error testing."""
    response = Mock()
    response.status_code = status_code
    response.headers = {}
    return response


def create_api_error(message: str, status_code: int) -> APIError:
    """Create an APIError with proper mock objects."""
    response = create_mock_response(status_code)
    request = Mock()
    error = APIError(message, request=request, body=None)
    error.status_code = status_code
    error.response = response
    return error


def create_rate_limit_error(message: str) -> RateLimitError:
    """Create a RateLimitError with proper mock objects."""
    response = create_mock_response(429)
    Mock()
    return RateLimitError(message, response=response, body=None)


def create_timeout_error(message: str) -> APITimeoutError:
    """Create an APITimeoutError with proper mock objects."""
    request = Mock()
    return APITimeoutError(request=request)


@pytest.fixture
def mock_anthropic():
    """Create a mock Anthropic client."""
    with patch("weft.ai.claude_client.Anthropic") as mock:
        yield mock.return_value


class TestClaudeClientInitialization:
    """Tests for ClaudeClient initialization."""

    def test_initialization_default_params(self, mock_anthropic: Mock) -> None:
        """Test client initialization with default parameters."""
        client = ClaudeClient(api_key="test-key")

        assert client.model == "claude-3-5-sonnet-20241022"
        assert client.max_tokens == 4096
        assert client.max_retries == 3
        assert client.client == mock_anthropic

    def test_initialization_custom_params(self, mock_anthropic: Mock) -> None:
        """Test client initialization with custom parameters."""
        client = ClaudeClient(
            api_key="test-key",
            model="claude-3-opus-20240229",
            max_tokens=8192,
            timeout=120,
            max_retries=5,
        )

        assert client.model == "claude-3-opus-20240229"
        assert client.max_tokens == 8192
        assert client.max_retries == 5

    def test_initialization_logs_model(
        self, mock_anthropic: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that initialization logs the model."""
        caplog.set_level(logging.INFO)
        ClaudeClient(api_key="test-key", model="claude-3-opus")

        assert "Initialized ClaudeClient with model: claude-3-opus" in caplog.text


class TestGenerate:
    """Tests for generate() method."""

    def test_generate_success(self, mock_anthropic: Mock) -> None:
        """Test successful generation."""
        # Mock response
        mock_response = Mock()
        mock_response.content = [Mock(text="Generated output")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)

        mock_anthropic.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        output = client.generate("Test prompt")

        assert output == "Generated output"
        mock_anthropic.messages.create.assert_called_once_with(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{"role": "user", "content": "Test prompt"}],
        )

    def test_generate_logs_prompt_hash_not_prompt(
        self, mock_anthropic: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that generate logs prompt hash, not full prompt (security)."""
        caplog.set_level(logging.INFO)
        mock_response = Mock()
        mock_response.content = [Mock(text="Output")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        client.generate("Super secret prompt")

        # Should log hash, not actual prompt
        assert "Super secret prompt" not in caplog.text
        assert "prompt_hash:" in caplog.text

    def test_generate_logs_token_usage(
        self, mock_anthropic: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that generate logs token usage."""
        caplog.set_level(logging.INFO)
        mock_response = Mock()
        mock_response.content = [Mock(text="Output")]
        mock_response.usage = Mock(input_tokens=123, output_tokens=456)
        mock_anthropic.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        client.generate("Test")

        assert "123 input" in caplog.text
        assert "456 output tokens" in caplog.text


class TestRetryLogic:
    """Tests for retry logic."""

    def test_retry_on_rate_limit(self, mock_anthropic: Mock) -> None:
        """Test retry logic on rate limit."""
        # First two calls fail, third succeeds
        mock_success = Mock()
        mock_success.content = [Mock(text="Success")]
        mock_success.usage = Mock(input_tokens=100, output_tokens=50)

        mock_anthropic.messages.create.side_effect = [
            create_rate_limit_error("Rate limited"),
            create_rate_limit_error("Rate limited"),
            mock_success,
        ]

        client = ClaudeClient(api_key="test-key", max_retries=3)

        with patch("time.sleep"):  # Don't actually sleep in tests
            output = client.generate("Test prompt")

        assert output == "Success"
        assert mock_anthropic.messages.create.call_count == 3

    def test_retry_on_timeout(self, mock_anthropic: Mock) -> None:
        """Test retry logic on timeout."""
        mock_success = Mock()
        mock_success.content = [Mock(text="Success")]
        mock_success.usage = Mock(input_tokens=100, output_tokens=50)

        mock_anthropic.messages.create.side_effect = [
            create_timeout_error("Timeout"),
            mock_success,
        ]

        client = ClaudeClient(api_key="test-key", max_retries=3)

        with patch("time.sleep"):
            output = client.generate("Test prompt")

        assert output == "Success"
        assert mock_anthropic.messages.create.call_count == 2

    def test_retry_on_5xx_error(self, mock_anthropic: Mock) -> None:
        """Test retry logic on 5xx server error."""
        # Create API error with 500 status code
        error = create_api_error("Server error", 500)

        mock_success = Mock()
        mock_success.content = [Mock(text="Success")]
        mock_success.usage = Mock(input_tokens=100, output_tokens=50)

        mock_anthropic.messages.create.side_effect = [error, mock_success]

        client = ClaudeClient(api_key="test-key", max_retries=3)

        with patch("time.sleep"):
            output = client.generate("Test prompt")

        assert output == "Success"
        assert mock_anthropic.messages.create.call_count == 2

    def test_exponential_backoff_timing(self, mock_anthropic: Mock) -> None:
        """Test that exponential backoff uses correct delays."""
        mock_success = Mock()
        mock_success.content = [Mock(text="Success")]
        mock_success.usage = Mock(input_tokens=100, output_tokens=50)

        mock_anthropic.messages.create.side_effect = [
            create_rate_limit_error("Rate limited"),
            create_rate_limit_error("Rate limited"),
            mock_success,
        ]

        client = ClaudeClient(api_key="test-key", max_retries=3)

        with patch("time.sleep") as mock_sleep:
            client.generate("Test prompt")

        # Verify exponential backoff: 1s (2^0), 2s (2^1)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # First retry: 2^0 = 1
        mock_sleep.assert_any_call(2)  # Second retry: 2^1 = 2

    def test_max_retries_exceeded_rate_limit(self, mock_anthropic: Mock) -> None:
        """Test exception when max retries exceeded on rate limit."""
        mock_anthropic.messages.create.side_effect = create_rate_limit_error("Rate limited")

        client = ClaudeClient(api_key="test-key", max_retries=2)

        with patch("time.sleep"), pytest.raises(RateLimitError):
            client.generate("Test prompt")

        assert mock_anthropic.messages.create.call_count == 2

    def test_max_retries_exceeded_timeout(self, mock_anthropic: Mock) -> None:
        """Test exception when max retries exceeded on timeout."""
        mock_anthropic.messages.create.side_effect = create_timeout_error("Timeout")

        client = ClaudeClient(api_key="test-key", max_retries=2)

        with patch("time.sleep"), pytest.raises(APITimeoutError):
            client.generate("Test prompt")

        assert mock_anthropic.messages.create.call_count == 2


class TestErrorHandling:
    """Tests for error handling."""

    def test_no_retry_on_4xx_client_error(self, mock_anthropic: Mock) -> None:
        """Test that 4xx errors (except 429) are not retried."""
        # Create API error with 400 status code
        error = create_api_error("Bad request", 400)

        mock_anthropic.messages.create.side_effect = error

        client = ClaudeClient(api_key="test-key", max_retries=3)

        with pytest.raises(APIError):
            client.generate("Test prompt")

        # Should not retry 4xx errors
        assert mock_anthropic.messages.create.call_count == 1

    def test_no_retry_on_401_unauthorized(self, mock_anthropic: Mock) -> None:
        """Test that 401 errors are not retried."""
        error = create_api_error("Unauthorized", 401)

        mock_anthropic.messages.create.side_effect = error

        client = ClaudeClient(api_key="test-key", max_retries=3)

        with pytest.raises(APIError):
            client.generate("Test prompt")

        assert mock_anthropic.messages.create.call_count == 1

    def test_retry_on_429_rate_limit_status(self, mock_anthropic: Mock) -> None:
        """Test that 429 status code IS retried (it's a rate limit)."""
        # 429 is special - it's a 4xx but should be retried
        error = create_api_error("Too many requests", 429)

        mock_success = Mock()
        mock_success.content = [Mock(text="Success")]
        mock_success.usage = Mock(input_tokens=100, output_tokens=50)

        mock_anthropic.messages.create.side_effect = [error, mock_success]

        client = ClaudeClient(api_key="test-key", max_retries=3)

        with patch("time.sleep"):
            output = client.generate("Test prompt")

        assert output == "Success"
        assert mock_anthropic.messages.create.call_count == 2

    def test_logs_errors(self, mock_anthropic: Mock, caplog: pytest.LogCaptureFixture) -> None:
        """Test that errors are logged."""
        caplog.set_level(logging.ERROR)
        error = create_api_error("Test error", 400)
        mock_anthropic.messages.create.side_effect = error

        client = ClaudeClient(api_key="test-key")

        with pytest.raises(APIError):
            client.generate("Test prompt")

        assert "Client error" in caplog.text


class TestGenerateWithMetadata:
    """Tests for generate_with_metadata() method."""

    def test_generate_with_metadata_success(self, mock_anthropic: Mock) -> None:
        """Test successful generation with metadata."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Generated output")]
        mock_response.usage = Mock(input_tokens=123, output_tokens=456)

        mock_anthropic.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key", model="claude-3-opus")
        result = client.generate_with_metadata("Test prompt")

        assert result["output"] == "Generated output"
        assert result["input_tokens"] == 123
        assert result["output_tokens"] == 456
        assert result["model"] == "claude-3-opus"

    def test_generate_with_metadata_calls_api(self, mock_anthropic: Mock) -> None:
        """Test that generate_with_metadata calls API correctly."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Output")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        client.generate_with_metadata("Test prompt")

        mock_anthropic.messages.create.assert_called_once_with(
            model="claude-3-5-sonnet-20241022",
            max_tokens=4096,
            messages=[{"role": "user", "content": "Test prompt"}],
        )

    def test_generate_with_metadata_logs_prompt_hash(
        self, mock_anthropic: Mock, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that generate_with_metadata logs prompt hash."""
        caplog.set_level(logging.INFO)
        mock_response = Mock()
        mock_response.content = [Mock(text="Output")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key")
        client.generate_with_metadata("Secret prompt")

        # Should log hash, not actual prompt
        assert "Secret prompt" not in caplog.text
        assert "prompt_hash:" in caplog.text


class TestIntegration:
    """Integration-style tests."""

    def test_full_workflow_with_retries(self, mock_anthropic: Mock) -> None:
        """Test full workflow with multiple retries."""
        # Simulate: rate limit -> timeout -> success
        mock_success = Mock()
        mock_success.content = [Mock(text="Final output")]
        mock_success.usage = Mock(input_tokens=100, output_tokens=50)

        mock_anthropic.messages.create.side_effect = [
            create_rate_limit_error("Rate limited"),
            create_timeout_error("Timeout"),
            mock_success,
        ]

        client = ClaudeClient(api_key="test-key", max_retries=3)

        with patch("time.sleep"):
            output = client.generate("Complex prompt")

        assert output == "Final output"
        assert mock_anthropic.messages.create.call_count == 3

    def test_respects_max_tokens_setting(self, mock_anthropic: Mock) -> None:
        """Test that max_tokens setting is respected."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Output")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key", max_tokens=2048)
        client.generate("Test")

        call_args = mock_anthropic.messages.create.call_args
        assert call_args.kwargs["max_tokens"] == 2048

    def test_respects_model_setting(self, mock_anthropic: Mock) -> None:
        """Test that model setting is respected."""
        mock_response = Mock()
        mock_response.content = [Mock(text="Output")]
        mock_response.usage = Mock(input_tokens=100, output_tokens=50)
        mock_anthropic.messages.create.return_value = mock_response

        client = ClaudeClient(api_key="test-key", model="claude-3-haiku")
        client.generate("Test")

        call_args = mock_anthropic.messages.create.call_args
        assert call_args.kwargs["model"] == "claude-3-haiku"
