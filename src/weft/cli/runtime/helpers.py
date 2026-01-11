"""Shared helper functions for runtime commands."""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Literal

from weft.config.errors import ConfigError
from weft.config.project import load_weftrc
from weft.utils.project import get_project_root

logger = logging.getLogger(__name__)


def sanitize_docker_project_name(name: str) -> str:
    """Sanitize project name for Docker Compose compatibility.

    Docker Compose requires project names to consist only of lowercase
    alphanumeric characters, hyphens, and underscores, and must start
    with a letter or number.

    Replaces invalid characters (like periods) with hyphens.
    """
    # Convert to lowercase
    sanitized = name.lower()

    # Replace any sequence of invalid characters with a single hyphen
    # Valid: a-z, 0-9, hyphen, underscore
    sanitized = re.sub(r"[^a-z0-9_-]+", "-", sanitized)

    # Remove leading/trailing hyphens or underscores
    sanitized = sanitized.strip("-_")

    # Ensure it starts with alphanumeric (not hyphen/underscore)
    if sanitized and not sanitized[0].isalnum():
        sanitized = "project-" + sanitized

    # Fallback if empty after sanitization
    if not sanitized:
        sanitized = "weft-project"

    return sanitized


def get_docker_compose_path() -> Path:
    """Get docker-compose.yml path.

    Looks in the following order:
    1. .weft/docker-compose.yml (project-specific, per-project config)
    2. templates/docker-compose.yml (fallback, weft installation)
    """
    # First, check for project-specific docker-compose.yml
    try:
        project_root = get_project_root()
        project_docker_compose = project_root / ".weft" / "docker-compose.yml"

        if project_docker_compose.exists():
            return project_docker_compose
    except Exception:
        # If we can't find project root, fall back to template
        pass

    # Fallback to weft package template
    weft_package_dir = Path(__file__).parent.parent.parent
    docker_compose_path = weft_package_dir / "templates" / "docker-compose.yml"

    if not docker_compose_path.exists():
        raise FileNotFoundError(
            "Weft docker-compose.yml not found.\n"
            "Expected at: {project_root}/.weft/docker-compose.yml\n"
            "Or fallback at: {docker_compose_path}\n"
            "Run 'weft init' to create project configuration."
        )

    return docker_compose_path


def validate_docker() -> bool:
    try:
        # Check docker binary exists
        subprocess.run(
            ["docker", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )

        # Check docker compose command
        subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            capture_output=True,
            text=True,
        )

        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_docker_daemon() -> bool:
    try:
        subprocess.run(
            ["docker", "ps"],
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def setup_docker_env(for_command: Literal["up", "down", "logs"] = "up") -> dict[str, str]:
    env = os.environ.copy()

    try:
        config = load_weftrc()
        if config:
            project_root = get_project_root()
            env["CODE_REPO_PATH"] = str(project_root)
            env["AI_HISTORY_PATH"] = str((project_root / config.ai.history_path).resolve())
            env["WEFT_AI_HISTORY_PATH"] = str((project_root / config.ai.history_path).resolve())
            env["WEFT_CODE_REPO_PATH"] = str(project_root)
            env["AI_BACKEND"] = config.ai.provider
            env["CLAUDE_MODEL"] = config.ai.model

            # Set COMPOSE_PROJECT_NAME for docker compose to namespace containers/networks
            # Docker Compose automatically prefixes all resource names with this value
            # Sanitize project name to meet Docker Compose requirements
            sanitized_name = sanitize_docker_project_name(config.project.name)
            if sanitized_name != config.project.name:
                logger.info(
                    f"Project name '{config.project.name}' sanitized to '{sanitized_name}' for Docker Compose compatibility. "
                    f"Docker Compose project names must contain only lowercase letters, numbers, hyphens, and underscores."
                )
            env["COMPOSE_PROJECT_NAME"] = sanitized_name

            # Set weft package directory for docker build context (only needed for up)
            if for_command == "up":
                # __file__ is src/weft/cli/runtime/helpers.py
                # Need to go up 5 levels to get to project root where Dockerfile.watcher is
                weft_package_dir = Path(__file__).parent.parent.parent.parent.parent
                env["WEFT_PACKAGE_DIR"] = str(weft_package_dir.resolve())

            # Get API key from environment
            api_key = os.getenv("WEFT_ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                env["ANTHROPIC_API_KEY"] = api_key
                env["WEFT_ANTHROPIC_API_KEY"] = api_key

            return env
    except (ConfigError, OSError, AttributeError) as e:
        # If config not found and command is 'up', raise error
        if for_command == "up":
            raise ConfigError(f"Failed to setup environment: {e}") from e

        # For 'down' and 'logs', set dummy values so docker-compose can parse the file
        env["CODE_REPO_PATH"] = "/tmp"
        env["AI_HISTORY_PATH"] = "/tmp"
        env["WEFT_AI_HISTORY_PATH"] = "/tmp"
        env["WEFT_CODE_REPO_PATH"] = "/tmp"
        env["AI_BACKEND"] = "anthropic"
        env["CLAUDE_MODEL"] = "claude-3-5-sonnet-20241022"
        env["COMPOSE_PROJECT_NAME"] = "weft"

    # Set dummy API key if not present (not needed for down/logs, but prevents warnings)
    if "ANTHROPIC_API_KEY" not in env:
        env["ANTHROPIC_API_KEY"] = "dummy"

    return env
