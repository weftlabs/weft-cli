"""Configuration settings loaded from environment and files."""

import contextlib
import os
from dataclasses import dataclass
from pathlib import Path

from .env import get_env_var, get_secret
from .project import load_weftrc


@dataclass
class Settings:
    code_repo_path: Path
    ai_history_path: Path
    anthropic_api_key: str
    model: str
    poll_interval: int
    log_level: str = "INFO"

    def __init__(
        self,
        code_repo_path: Path,
        ai_history_path: Path,
        anthropic_api_key: str | None = None,
        model: str | None = None,
        poll_interval: int = 2,
        log_level: str = "INFO",
    ):
        self.code_repo_path = (
            Path(code_repo_path) if not isinstance(code_repo_path, Path) else code_repo_path
        )
        self.ai_history_path = (
            Path(ai_history_path) if not isinstance(ai_history_path, Path) else ai_history_path
        )
        self.anthropic_api_key = anthropic_api_key or ""
        self.model = model or "claude-3-5-sonnet-20241022"
        self.poll_interval = poll_interval
        self.log_level = log_level.upper() if log_level else "INFO"


def get_settings() -> Settings:
    # Try to load from .weftrc.yaml first
    config = load_weftrc()

    # Get code repo path
    code_repo_path_str = get_env_var("CODE_REPO_PATH")
    if not code_repo_path_str:
        # Try to find project root, fall back to cwd
        from weft.utils.project import find_project_root

        project_root = find_project_root()
        code_repo_path_str = str(project_root) if project_root else os.getcwd()

    # Expand ~ in paths
    code_repo_path_str = os.path.expanduser(code_repo_path_str)

    # Get AI history path - try .weftrc.yaml first, then environment
    ai_history_path_str = get_env_var("AI_HISTORY_PATH")
    if not ai_history_path_str and config:
        # Use path from .weftrc.yaml
        ai_history_path_str = config.ai.history_path

    if not ai_history_path_str:
        raise ValueError(
            "WEFT_AI_HISTORY_PATH environment variable or .weftrc.yaml configuration is required.\n"
            "Run 'weft init' to create .weftrc.yaml, or set WEFT_AI_HISTORY_PATH environment variable."
        )

    # Expand ~ in paths and resolve relative to project root
    ai_history_path_str = os.path.expanduser(ai_history_path_str)
    if not os.path.isabs(ai_history_path_str):
        ai_history_path_str = str((Path(code_repo_path_str) / ai_history_path_str).resolve())

    # Get API key - check both ANTHROPIC_API_KEY and WEFT_ANTHROPIC_API_KEY
    # Note: ANTHROPIC_API_KEY without prefix for SDK compatibility
    anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not anthropic_api_key:
        # Try with WEFT_ prefix (default to empty string if not found)
        with contextlib.suppress(Exception):
            anthropic_api_key = get_secret("ANTHROPIC_API_KEY")  # Will check WEFT_ANTHROPIC_API_KEY

    # Get model - try environment first, then .weftrc.yaml, then default
    model = get_env_var("MODEL")
    if not model and config:
        model = config.ai.model
    if not model:
        model = "claude-3-5-sonnet-20241022"

    # Get poll interval
    poll_interval_str = get_env_var("POLL_INTERVAL") or "2"
    try:
        poll_interval = int(poll_interval_str)
    except ValueError:
        poll_interval = 2

    # Get log level
    log_level = get_env_var("LOG_LEVEL") or "INFO"

    return Settings(
        code_repo_path=Path(code_repo_path_str),
        ai_history_path=Path(ai_history_path_str),
        anthropic_api_key=anthropic_api_key,
        model=model,
        poll_interval=poll_interval,
        log_level=log_level.upper(),
    )


def load_settings(
    code_repo_path: Path | None = None,
    ai_history_path: Path | None = None,
) -> Settings:
    settings = get_settings()

    # Apply overrides
    if code_repo_path:
        settings.code_repo_path = code_repo_path
    if ai_history_path:
        settings.ai_history_path = ai_history_path

    return settings


def reset_settings() -> None:
    pass


__all__ = ["Settings", "get_settings", "load_settings", "reset_settings"]
