"""Main CLI entry point for weft command.

This module provides the main CLI group and registers all subcommands.
"""

import os
import shutil
import subprocess

import click

from weft import __version__

# Import commands
from weft.cli.feature import (
    feature_create,
    feature_drop,
    feature_list,
    feature_start,
    review,
)
from weft.cli.init import project_init
from weft.cli.runtime import down, logs, up
from weft.cli.status import status_command


def validate_environment(require_api_key: bool = False) -> None:
    """Validate required dependencies and configuration."""
    errors = []

    # Check git is installed
    if not shutil.which("git"):
        errors.append("❌ Git is not installed or not in PATH")
        errors.append("   Install: https://git-scm.com/downloads")

    # Check git is configured
    if shutil.which("git"):
        try:
            subprocess.run(
                ["git", "config", "user.name"],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            errors.append("❌ Git user.name not configured")
            errors.append('   Run: git config --global user.name "Your Name"')

        try:
            subprocess.run(
                ["git", "config", "user.email"],
                capture_output=True,
                check=True,
            )
        except subprocess.CalledProcessError:
            errors.append("❌ Git user.email not configured")
            errors.append('   Run: git config --global user.email "you@example.com"')

    # Check API key if required
    if require_api_key and not os.getenv("ANTHROPIC_API_KEY"):
        errors.append("❌ ANTHROPIC_API_KEY environment variable not set")
        errors.append("   Set in .env file or export ANTHROPIC_API_KEY=your-key")
        errors.append("   Get API key: https://console.anthropic.com/settings/keys")

    if errors:
        for error in errors:
            click.echo(error, err=True)
        raise click.Abort()


@click.group()
@click.option(
    "--config",
    type=click.Path(exists=True),
    help="Path to config file (default: .env)",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.version_option(version=__version__, prog_name="weft")
@click.pass_context
def cli(ctx, config: str | None, verbose: bool):  # type: ignore[no-untyped-def]
    """Weft - AI-assisted development with role-based agents.

    This tool manages AI-assisted feature development using role-based
    agents, git worktrees, and file-based task queues.

    Examples:

        # Initialize a new project (first time)
        weft init

        # Create a new feature (talk with meta agent)
        weft feature create user-auth

        # Start agents to generate implementation
        weft feature start user-auth

        # Review and decide (accept/drop/continue)
        weft feature review user-auth

    For more information, see: https://github.com/weftlabs/weft-cli
    """
    # Ensure context object exists
    ctx.ensure_object(dict)

    # Store global options in context
    ctx.obj["config"] = config
    ctx.obj["verbose"] = verbose

    # Load config if specified
    if config:
        from dotenv import load_dotenv

        load_dotenv(config)
    else:
        # Try loading from default .env file in project root

        from dotenv import load_dotenv

        from weft.utils.project import get_project_root

        try:
            project_root = get_project_root()
            env_path = project_root / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=env_path)
            else:
                # Fallback to current directory for projects not initialized with weft
                load_dotenv()
        except Exception:
            # If we can't find project root, try current directory
            load_dotenv()

    # Validate environment for most commands (except --version, --help)
    if ctx.invoked_subcommand not in [None]:
        validate_environment(require_api_key=False)


# Feature command group
@cli.group(name="feature")
def feature_group():  # type: ignore[no-untyped-def]
    """Manage features (create, start, list, review, drop)."""
    pass


# Register feature subcommands
feature_group.add_command(feature_create, name="create")
feature_group.add_command(feature_start, name="start")
feature_group.add_command(feature_list, name="list")
feature_group.add_command(status_command, name="status")
feature_group.add_command(review, name="review")
feature_group.add_command(feature_drop, name="drop")

# Register project-level commands
cli.add_command(project_init, name="init")
cli.add_command(up, name="up")
cli.add_command(down, name="down")
cli.add_command(logs, name="logs")


if __name__ == "__main__":
    cli()
