"""Weft configuration system.

This module provides a formal, structured configuration system with:
- Strict WEFT_* environment variable namespacing
- Project configuration (.weftrc.yaml)
- Runtime directory (.weft/)
- User configuration (~/.config/weft/config.yaml)
- Configuration precedence resolution
"""

from .env import (
    ensure_no_env_in_history,
    get_env_var,
    get_secret,
    load_weft_env_vars,
    validate_required_secrets,
)
from .errors import ConfigError, SecurityError
from .project import (
    AgentsConfig,
    AIConfig,
    GitConfig,
    GitWorktreeConfig,
    PathsConfig,
    ProjectConfig,
    WeftRC,
    create_default_weftrc,
    load_weftrc,
    validate_weftrc,
)
from .resolver import ConfigResolver
from .runtime import WeftRuntime
from .user import (
    UserConfig,
    UserDefaults,
    UserEditor,
    UserGit,
    UserNotifications,
    create_user_config,
    get_user_config_path,
    load_user_config,
)

__all__ = [
    # Errors
    "ConfigError",
    "SecurityError",
    # Environment variables
    "load_weft_env_vars",
    "validate_required_secrets",
    "ensure_no_env_in_history",
    "get_env_var",
    "get_secret",
    # Project configuration
    "WeftRC",
    "ProjectConfig",
    "AIConfig",
    "AgentsConfig",
    "GitConfig",
    "GitWorktreeConfig",
    "PathsConfig",
    "load_weftrc",
    "validate_weftrc",
    "create_default_weftrc",
    # User configuration
    "UserConfig",
    "UserDefaults",
    "UserNotifications",
    "UserEditor",
    "UserGit",
    "load_user_config",
    "get_user_config_path",
    "create_user_config",
    # Runtime directory
    "WeftRuntime",
    # Configuration resolution
    "ConfigResolver",
]


def load_config(project_path: str = ".", cli_args: dict = None):
    """Load complete configuration from all sources.

    This is the main entry point for loading configuration.
    """
    from pathlib import Path

    # Load project config
    weftrc_path = Path(project_path) / ".weftrc.yaml"
    project_config = load_weftrc(weftrc_path)

    # Load user config
    user_config = load_user_config()

    # Create resolver
    defaults = {
        "ai.provider": "anthropic",
        "ai.model_profile": "standard",
        "log_level": "info",
    }

    resolver = ConfigResolver(
        cli_args=cli_args or {},
        project_config=project_config,
        user_config=user_config,
        defaults=defaults,
    )

    return project_config, user_config, resolver
