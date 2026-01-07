"""Runtime management commands (up, down, logs)."""

import subprocess
from pathlib import Path
from typing import Optional

import click

from weft.config.errors import ConfigError
from weft.config.project import load_weftrc
from weft.utils.project import get_project_root


def validate_docker() -> bool:
    """Check if docker is installed and running.
    """
    try:
        # Check docker binary exists
        subprocess.run(
            ["docker", "--version"],
            check=True,
            capture_output=True,
            text=True,
        )

        # Check docker compose command
        result = subprocess.run(
            ["docker", "compose", "version"],
            check=True,
            capture_output=True,
            text=True,
        )

        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_docker_daemon() -> bool:
    """Check if docker daemon is running.
    """
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


@click.command()
@click.option(
    "--detach/--no-detach",
    "-d/-D",
    default=True,
    help="Run containers in background (default: detached)",
)
def up(detach: bool) -> None:
    """Start the docker runtime environment.

    Starts docker-compose services including agent watchers for all
    enabled agents defined in .weftrc.yaml.

    Examples:
        weft up           # Start all services in background
        weft up --no-detach  # Start and attach to logs
    """
    # 1. Validate docker is installed
    if not validate_docker():
        click.echo("❌ Error: Docker is not installed or not in PATH", err=True)
        click.echo("\nPlease install Docker:", err=True)
        click.echo("  macOS: https://docs.docker.com/desktop/mac/install/", err=True)
        click.echo("  Linux: https://docs.docker.com/engine/install/", err=True)
        click.echo("  Windows: https://docs.docker.com/desktop/windows/install/", err=True)
        raise click.Abort()

    # 2. Check docker daemon is running
    if not check_docker_daemon():
        click.echo("❌ Error: Docker daemon is not running", err=True)
        click.echo("\nPlease start Docker Desktop or the Docker daemon", err=True)
        raise click.Abort()

    # 3. Load config to get enabled agents
    config = load_weftrc()
    if not config:
        click.echo("❌ Error: .weftrc.yaml not found", err=True)
        click.echo("Run 'weft project-init' first to initialize the project", err=True)
        raise click.Abort()

    enabled_agents = config.agents.enabled
    if not enabled_agents:
        click.echo("⚠ Warning: No agents enabled in .weftrc.yaml", err=True)
        click.echo("Continuing anyway...", err=True)

    # 4. Find project root
    try:
        project_root = get_project_root()
    except ConfigError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

    # 5. Check if docker-compose.yml exists
    docker_compose_path = project_root / "docker-compose.yml"
    if not docker_compose_path.exists():
        click.echo(f"❌ Error: docker-compose.yml not found at: {docker_compose_path}", err=True)
        click.echo("This file should define the watcher services", err=True)
        raise click.Abort()

    # 5. Start docker-compose services
    click.echo("🚀 Starting Weft runtime...\n")
    click.echo(f"Enabled agents: {', '.join(enabled_agents)}\n")

    # Build service names from enabled agents
    services = [f"watcher-{agent}" for agent in enabled_agents]

    try:
        cmd = ["docker", "compose", "-f", str(docker_compose_path), "up"]
        if detach:
            cmd.append("-d")
        cmd.extend(services)

        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Show docker-compose output
        )

        if detach:
            click.echo("\n✅ Runtime started successfully!\n")
            click.echo("Services running:")
            for agent in enabled_agents:
                click.echo(f"  • watcher-{agent}")

            click.echo("\n📋 Next steps:")
            click.echo("  • View logs: weft logs <agent>")
            click.echo("  • Create feature: weft feature create <name>")
            click.echo("  • Stop runtime: weft down\n")

    except subprocess.CalledProcessError as e:
        click.echo(f"\n❌ Error starting runtime: {e}", err=True)
        raise click.Abort()


@click.command()
@click.option(
    "--volumes",
    "-v",
    is_flag=True,
    help="Remove named volumes declared in docker-compose.yml",
)
def down(volumes: bool) -> None:
    """Stop the docker runtime environment.

    Stops all running watcher services and optionally removes volumes.

    Examples:
        weft down           # Stop services
        weft down --volumes # Stop and remove volumes
    """
    # 1. Validate docker
    if not validate_docker():
        click.echo("❌ Error: Docker is not installed", err=True)
        raise click.Abort()

    # 2. Find project root
    try:
        project_root = get_project_root()
    except ConfigError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

    # 3. Check if docker-compose.yml exists
    docker_compose_path = project_root / "docker-compose.yml"
    if not docker_compose_path.exists():
        click.echo(f"❌ Error: docker-compose.yml not found at: {docker_compose_path}", err=True)
        raise click.Abort()

    click.echo("🛑 Stopping Weft runtime...\n")

    try:
        cmd = ["docker", "compose", "-f", str(docker_compose_path), "down"]
        if volumes:
            cmd.append("--volumes")

        subprocess.run(cmd, check=True)

        click.echo("✅ Runtime stopped successfully\n")

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Error stopping runtime: {e}", err=True)
        raise click.Abort()


@click.command()
@click.argument("agent", required=False)
@click.option(
    "--follow",
    "-f",
    is_flag=True,
    help="Follow log output (stream live logs)",
)
@click.option(
    "--tail",
    "-n",
    type=int,
    default=100,
    help="Number of lines to show from end of logs (default: 100)",
)
def logs(agent: Optional[str], follow: bool, tail: int) -> None:
    """View logs for specific agent watcher.

    If no agent is specified, shows logs for all services.

    Examples:
        weft logs meta           # View meta agent logs
        weft logs meta --follow  # Stream meta agent logs live
        weft logs --tail 50      # Show last 50 lines from all services
    """
    # 1. Validate docker
    if not validate_docker():
        click.echo("❌ Error: Docker is not installed", err=True)
        raise click.Abort()

    # 2. Find project root
    try:
        project_root = get_project_root()
    except ConfigError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

    docker_compose_path = project_root / "docker-compose.yml"

    # 3. Build service name
    if agent:
        service = f"watcher-{agent}"
        click.echo(f"📋 Logs for watcher-{agent}:\n")
    else:
        service = None
        click.echo("📋 Logs for all services:\n")

    try:
        cmd = ["docker", "compose", "-f", str(docker_compose_path), "logs"]

        if follow:
            cmd.append("--follow")

        cmd.extend(["--tail", str(tail)])

        if service:
            cmd.append(service)

        # Run without check=True so user can Ctrl+C to exit
        subprocess.run(cmd)

    except KeyboardInterrupt:
        click.echo("\n\n✅ Stopped following logs")
    except subprocess.CalledProcessError as e:
        click.echo(f"\n❌ Error viewing logs: {e}", err=True)
        raise click.Abort()
