"""Configuration resolution with precedence: CLI > project > user > ENV > defaults."""

import os
from typing import Any

from .errors import ConfigError
from .project import WeftRC
from .user import UserConfig


class ConfigResolver:
    """Secrets only from ENV; others follow precedence order."""

    def __init__(
        self,
        cli_args: dict[str, Any] = None,
        project_config: WeftRC | None = None,
        user_config: UserConfig | None = None,
        defaults: dict[str, Any] = None,
    ):
        self.cli_args = cli_args or {}
        self.project_config = project_config
        self.user_config = user_config
        self.defaults = defaults or {}

    def resolve(self, key: str, secret: bool = False) -> Any:
        # Secrets can ONLY come from ENV
        if secret:
            env_key = f"WEFT_{key.upper().replace('.', '_')}"
            if env_key in os.environ:
                return os.environ[env_key]
            raise ConfigError(
                f"Required secret not found: {env_key}\n"
                f"Secrets must be provided via WEFT_* environment variables.\n"
                f"Set with: export {env_key}=your-secret-here"
            )

        # Check CLI args first
        if key in self.cli_args and self.cli_args[key] is not None:
            return self.cli_args[key]

        # Check project config
        if self.project_config:
            value = self._get_nested(self.project_config, key)
            if value is not None:
                return value

        # Check user config
        if self.user_config:
            value = self._get_nested(self.user_config, key)
            if value is not None:
                return value

        # Check ENV vars
        env_key = f"WEFT_{key.upper().replace('.', '_')}"
        if env_key in os.environ:
            return os.environ[env_key]

        # Check defaults
        if key in self.defaults and self.defaults[key] is not None:
            return self.defaults[key]

        raise ConfigError(f"Configuration key not found: {key}")

    def resolve_optional(self, key: str, default: Any = None) -> Any:
        try:
            return self.resolve(key)
        except ConfigError:
            return default

    def _get_nested(self, config: Any, key: str) -> Any | None:
        parts = key.split(".")
        current = config

        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            else:
                return None

        return current

    def get_all_config(self) -> dict[str, Any]:
        config = {}

        # Add defaults first
        config.update(self.defaults)

        # Add ENV vars
        for key, value in os.environ.items():
            if key.startswith("WEFT_"):
                internal_key = key[5:].lower().replace("_", ".")
                config[internal_key] = value

        # Add user config
        if self.user_config:
            config.update(self._flatten_config(self.user_config))

        # Add project config
        if self.project_config:
            config.update(self._flatten_config(self.project_config))

        # Add CLI args
        config.update(self.cli_args)

        return config

    def _flatten_config(self, config: Any, prefix: str = "") -> dict[str, Any]:
        result = {}

        if hasattr(config, "model_dump"):
            # Pydantic model
            data = config.model_dump()
        elif isinstance(config, dict):
            data = config
        else:
            return result

        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key

            if isinstance(value, dict) or hasattr(value, "model_dump"):
                result.update(self._flatten_config(value, full_key))
            else:
                result[full_key] = value

        return result
