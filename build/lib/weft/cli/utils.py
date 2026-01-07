"""CLI utility functions for formatting and user interaction."""

from datetime import datetime
from pathlib import Path

import click

from weft.config.settings import Settings, get_settings


def format_timestamp(dt: datetime | None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Format datetime for display."""
    if dt is None:
        return "Never"
    return dt.strftime(format_str)


def format_path(path: Path, relative_to: Path | None = None) -> str:
    """Format path for display."""
    if relative_to:
        try:
            return str(path.relative_to(relative_to))
        except ValueError:
            # Path is not relative to base
            pass

    return str(path)


def confirm_action(message: str, default: bool = False) -> bool:
    """Prompt user for confirmation."""
    return click.confirm(message, default=default)


def echo_success(message: str) -> None:
    """Print success message in green."""
    click.echo(click.style(f"✓ {message}", fg="green"))


def echo_error(message: str) -> None:
    """Print error message in red."""
    click.echo(click.style(f"✗ {message}", fg="red"), err=True)


def echo_warning(message: str) -> None:
    """Print warning message in yellow."""
    click.echo(click.style(f"⚠ {message}", fg="yellow"))


def echo_info(message: str) -> None:
    """Print info message."""
    click.echo(f"ℹ {message}")


def safe_get_settings() -> Settings:
    """Load settings with error handling and user-friendly messages."""
    try:
        return get_settings()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort() from e


def safe_get_docker_compose_path() -> Path:
    """Get docker-compose path with error handling."""
    from weft.cli.runtime.helpers import get_docker_compose_path

    try:
        return get_docker_compose_path()
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort() from e


def echo_separator(width: int = 70, char: str = "=") -> None:
    """Print a separator line."""
    click.echo(char * width)


def echo_section_start(title: str, width: int = 70) -> None:
    """Print section header with separator."""
    click.echo(f"\n{'=' * width}")
    click.echo(title)
    click.echo(f"{'=' * width}\n")


def echo_section_end(width: int = 70) -> None:
    """Print section footer separator."""
    click.echo(f"{'=' * width}\n")
