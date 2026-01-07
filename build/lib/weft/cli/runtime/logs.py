"""View logs for agent watchers."""

import subprocess

import click

from weft.cli.runtime.helpers import (
    get_docker_compose_path,
    setup_docker_env,
    validate_docker,
)


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
@click.option(
    "--clear",
    is_flag=True,
    help="Clear all logs (or specific agent logs if agent specified)",
)
def logs(agent: str | None, follow: bool, tail: int, clear: bool) -> None:
    """View logs for specific agent watcher.

    If no agent is specified, shows logs for all services.

    Examples:
        weft logs meta           # View meta agent logs
        weft logs meta --follow  # Stream meta agent logs live
        weft logs --tail 50      # Show last 50 lines from all services
        weft logs --clear        # Clear all agent logs
        weft logs meta --clear   # Clear only meta agent logs
    """
    # Validate docker
    if not validate_docker():
        click.echo("❌ Error: Docker is not installed", err=True)
        raise click.Abort()

    # Get weft's docker-compose.yml
    try:
        docker_compose_path = get_docker_compose_path()
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort() from e

    # Set up environment variables
    env = setup_docker_env(for_command="logs")

    # Handle --clear flag
    if clear:
        click.echo("🧹 Clearing logs...")
        click.echo("\n💡 To completely clear Docker logs, restart the runtime:")
        click.echo("   weft down && weft up")
        click.echo("\nThis will stop all containers and restart them with fresh logs.\n")
        return

    # Build service name
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
        subprocess.run(cmd, env=env)

    except KeyboardInterrupt:
        click.echo("\n\n✅ Stopped following logs")
    except subprocess.CalledProcessError as e:
        click.echo(f"\n❌ Error viewing logs: {e}", err=True)
        raise click.Abort() from e
