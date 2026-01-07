"""User configuration from ~/.config/weft/config.yaml."""

import os
from pathlib import Path

import yaml
from pydantic import BaseModel

from .errors import ConfigError
from .project import contains_secrets


class UserDefaults(BaseModel):
    provider: str = "anthropic"
    model_profile: str = "standard"
    log_level: str = "info"


class UserNotifications(BaseModel):
    enabled: bool = False
    sound: bool = True


class UserEditor(BaseModel):
    command: str = "vim"
    args: list[str] = []


class UserGit(BaseModel):
    auto_commit: bool = False
    commit_message: str = "weft: {agent} completed {feature}"


class UserConfig(BaseModel):
    defaults: UserDefaults = UserDefaults()
    notifications: UserNotifications = UserNotifications()
    editor: UserEditor = UserEditor()
    git: UserGit = UserGit()


def get_user_config_path() -> Path:
    """Uses XDG_CONFIG_HOME if set, otherwise ~/.config."""
    # Use XDG_CONFIG_HOME if set, otherwise ~/.config
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg_config) if xdg_config else Path.home() / ".config"

    return base / "weft" / "config.yaml"


def load_user_config() -> UserConfig:
    """Returns defaults if file not found or invalid."""
    path = get_user_config_path()

    if not path.exists():
        return UserConfig()

    try:
        with open(path) as f:
            data = yaml.safe_load(f)

        # Check for secrets
        if contains_secrets(data):
            raise ConfigError(
                f"Security violation: Secrets detected in {path}\n"
                "User config must not contain secrets.\n"
                "Use WEFT_* environment variables for API keys."
            )

        return UserConfig(**data)

    except Exception as e:
        # If user config is invalid, warn but continue with defaults
        print(f"Warning: Could not load user config: {e}")
        return UserConfig()


def create_user_config(path: Path = None) -> UserConfig:
    if path is None:
        path = get_user_config_path()

    # Ensure directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Create default config
    default_config = UserConfig()

    # Write to file
    with open(path, "w") as f:
        yaml.dump(default_config.model_dump(), f, default_flow_style=False)

    return default_config
