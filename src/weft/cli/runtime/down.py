"""Stop docker runtime environment."""

import subprocess

import click

from weft.cli.runtime.helpers import (
    get_docker_compose_path,
    setup_docker_env,
    validate_docker,
)


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
    env = setup_docker_env(for_command="down")

    click.echo("🛑 Stopping Weft runtime...\n")

    try:
        cmd = ["docker", "compose", "-f", str(docker_compose_path), "down"]
        if volumes:
            cmd.append("--volumes")

        subprocess.run(cmd, check=True, env=env)

        click.echo("✅ Runtime stopped successfully\n")

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Error stopping runtime: {e}", err=True)
        raise click.Abort() from e
