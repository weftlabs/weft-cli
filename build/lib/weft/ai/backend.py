"""AI backend abstraction layer.

Provides an abstraction for AI backends to support multiple providers
(Claude, local LLMs, gateway proxies) with a unified interface.
"""

from abc import ABC, abstractmethod
from typing import Any

from weft.ai.claude_client import ClaudeClient
from weft.config.settings import get_settings


class AIBackend(ABC):
    @abstractmethod
    def generate(self, prompt: str, conversation_history: list[dict] | None = None) -> str:
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        pass


class ClaudeBackend(AIBackend):
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022", **kwargs):
        self.client = ClaudeClient(api_key=api_key, model=model, **kwargs)
        self.model = model

    def generate(self, prompt: str, conversation_history: list[dict] | None = None) -> str:
        return self.client.generate(prompt, conversation_history)

    def get_model_info(self) -> dict[str, Any]:
        return {
            "backend": "claude",
            "model": self.model,
            "max_tokens": self.client.max_tokens,
            "provider": "anthropic",
        }


class LocalLLMBackend(AIBackend):
    """Placeholder for M4 - will support Ollama, LLaMA, etc."""

    def __init__(self, **kwargs):
        pass

    def generate(self, prompt: str, conversation_history: list[dict] | None = None) -> str:
        raise NotImplementedError(
            "Local LLM backend not yet implemented. "
            "This will be added in M4 (Enterprise Features). "
            "For now, use backend_type='claude'."
        )

    def get_model_info(self) -> dict[str, Any]:
        return {"backend": "local", "model": "not-implemented", "provider": "local"}


def create_backend(backend_type: str, **kwargs) -> AIBackend:
    if backend_type == "claude":
        return ClaudeBackend(**kwargs)
    elif backend_type == "local":
        return LocalLLMBackend(**kwargs)
    else:
        raise ValueError(
            f"Unknown backend type: {backend_type}. " f"Supported types: claude, local"
        )


def create_backend_from_config() -> AIBackend:
    settings = get_settings()

    backend_type = getattr(settings, "ai_backend", "claude")
    backend_config = getattr(settings, "ai_backend_config", {})

    # Add API key from settings if using Claude
    if backend_type == "claude":
        backend_config["api_key"] = settings.anthropic_api_key
        backend_config.setdefault("model", settings.model)

    return create_backend(backend_type, **backend_config)
