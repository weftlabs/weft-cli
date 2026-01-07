"""Claude API client with retry logic and audit logging."""

import logging
import time

from anthropic import Anthropic, APIError, APITimeoutError, RateLimitError

from weft.audit.hashing import sha256_hash
from weft.constants import AI_REQUEST_TIMEOUT, DEFAULT_MAX_RETRIES, DEFAULT_MAX_TOKENS

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Logs prompt hashes instead of full prompts for security."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout: int = AI_REQUEST_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        self.client = Anthropic(api_key=api_key, timeout=timeout)
        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = max_retries

        logger.info(f"Initialized ClaudeClient with model: {model}")

    def generate(self, prompt: str, conversation_history: list[dict] | None = None) -> str:
        """Retries on rate limits, timeouts, and 5xx errors."""
        prompt_hash = sha256_hash(prompt)
        logger.info(
            f"Generating with Claude (model: {self.model}, " f"prompt_hash: {prompt_hash[:16]}...)"
        )

        # Build messages array
        messages = []
        if conversation_history:
            messages.extend(conversation_history)
            logger.info(f"Using conversation history with {len(conversation_history)} message(s)")

        # Add current prompt
        messages.append({"role": "user", "content": prompt})

        for attempt in range(self.max_retries):
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    messages=messages,  # type: ignore[arg-type]
                )

                output = response.content[0].text  # type: ignore[union-attr]

                logger.info(
                    f"Generated {len(output)} chars, "
                    f"used {response.usage.input_tokens} input + "
                    f"{response.usage.output_tokens} output tokens"
                )

                return output

            except RateLimitError as e:
                logger.warning(f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise

            except APITimeoutError as e:
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = 2**attempt
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise

            except APIError as e:
                # Don't retry 4xx errors (except 429)
                if (
                    hasattr(e, "status_code")
                    and 400 <= e.status_code < 500
                    and e.status_code != 429
                ):
                    logger.error(f"Client error: {e}")
                    raise

                logger.warning(f"API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    delay = 2**attempt
                    logger.info(f"Retrying in {delay}s...")
                    time.sleep(delay)
                else:
                    raise

        raise APIError("Max retries exceeded")  # type: ignore[call-arg]

    def generate_with_metadata(self, prompt: str) -> dict:
        """Does not include retry logic - use generate() for production."""
        prompt_hash = sha256_hash(prompt)
        logger.info(f"Generating with metadata (prompt_hash: {prompt_hash[:16]}...)")

        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        return {
            "output": response.content[0].text,  # type: ignore[union-attr]
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "model": self.model,
        }
