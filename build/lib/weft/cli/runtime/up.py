"""Start docker runtime environment."""

import subprocess

import click

from weft.cli.runtime.helpers import (
    check_docker_daemon,
    get_docker_compose_path,
    setup_docker_env,
    validate_docker,
)
from weft.config.project import load_weftrc


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
    # Validate docker is installed
    if not validate_docker():
        click.echo("❌ Error: Docker is not installed or not in PATH", err=True)
        click.echo("\nPlease install Docker:", err=True)
        click.echo("  macOS: https://docs.docker.com/desktop/mac/install/", err=True)
        click.echo("  Linux: https://docs.docker.com/engine/install/", err=True)
        click.echo("  Windows: https://docs.docker.com/desktop/windows/install/", err=True)
        raise click.Abort()

    # Check docker daemon is running
    if not check_docker_daemon():
        click.echo("❌ Error: Docker daemon is not running", err=True)
        click.echo("\nPlease start Docker Desktop or the Docker daemon", err=True)
        raise click.Abort()

    # Load config to get enabled agents
    config = load_weftrc()
    if not config:
        click.echo("❌ Error: .weftrc.yaml not found", err=True)
        click.echo("Run 'weft init' first to initialize the project", err=True)
        raise click.Abort()

    enabled_agents = config.agents.enabled
    if not enabled_agents:
        click.echo("⚠ Warning: No agents enabled in .weftrc.yaml", err=True)
        click.echo("Continuing anyway...", err=True)

    # Get weft's docker-compose.yml
    try:
        docker_compose_path = get_docker_compose_path()
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort() from e

    # Set up environment variables for docker-compose
    try:
        env = setup_docker_env(for_command="up")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort() from e

    # Start docker-compose services
    click.echo("🚀 Starting Weft runtime...\n")
    click.echo(f"Enabled agents: {', '.join(enabled_agents)}\n")

    # Build service names from enabled agents
    services = [f"watcher-{agent}" for agent in enabled_agents]

    try:
        cmd = ["docker", "compose", "-f", str(docker_compose_path), "up"]
        if detach:
            cmd.append("-d")
        cmd.extend(services)

        subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Show docker-compose output
            env=env,
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
        raise click.Abort() from e
