"""Environment variable loading with WEFT_ prefix."""

import os
from pathlib import Path

from .errors import ConfigError, SecurityError


def load_weft_env_vars() -> dict[str, str]:
    """Load only WEFT_* prefixed environment variables."""
    weft_vars = {}
    for key, value in os.environ.items():
        if key.startswith("WEFT_"):
            # Strip WEFT_ prefix for internal use
            internal_key = key[5:]  # Remove "WEFT_"
            weft_vars[internal_key] = value
    return weft_vars


def validate_required_secrets() -> None:
    """Validate required secret environment variables are present."""
    required_secrets = ["WEFT_ANTHROPIC_API_KEY"]
    missing = [s for s in required_secrets if s not in os.environ]

    if missing:
        raise ConfigError(
            f"Required environment variables missing: {', '.join(missing)}\n"
            f"Set them with: export {missing[0]}=your-key-here"
        )


def ensure_no_env_in_history(path: Path) -> None:
    """Validate no WEFT_* variables leaked into history files.

    This is a safety check to ensure environment variables were never
    written to disk. Should be run periodically on .weft/history.
    """
    if not path.exists():
        return

    # Patterns that indicate environment variables
    dangerous_patterns = [
        "WEFT_ANTHROPIC_API_KEY",
        "WEFT_OPENAI_API_KEY",
        "sk-ant-",  # Anthropic API key prefix
        "sk-",  # OpenAI API key prefix
    ]

    for file_path in path.rglob("*"):
        if not file_path.is_file():
            continue

        # Only check text files
        if file_path.suffix not in [".md", ".txt", ".log", ".json", ".yaml"]:
            continue

        try:
            content = file_path.read_text()
            for pattern in dangerous_patterns:
                if pattern in content:
                    raise SecurityError(
                        f"Potential secret found in {file_path}\n"
                        f"Pattern: {pattern}\n"
                        f"Secrets must never be written to .weft/history\n"
                        f"This is a critical security violation."
                    )
        except UnicodeDecodeError:
            # Skip binary files
            continue


def get_env_var(key: str, default: str = None) -> str:
    """Get a WEFT_* prefixed environment variable."""
    full_key = f"WEFT_{key.upper()}"
    return os.environ.get(full_key, default)


def get_secret(key: str) -> str:
    """Get a secret from environment variables."""
    full_key = f"WEFT_{key.upper()}"
    value = os.environ.get(full_key)

    if not value:
        raise ConfigError(
            f"Required secret not found: {full_key}\n"
            f"Secrets must be provided via environment variables.\n"
            f"Set with: export {full_key}=your-secret-here"
        )

    return value
