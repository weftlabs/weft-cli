"""Feature status display commands."""

import logging
from datetime import datetime
from pathlib import Path

import click

from weft.config.settings import get_settings
from weft.git.worktree import get_worktree_status, list_worktrees

logger = logging.getLogger(__name__)


def get_feature_status(code_repo_path: Path, ai_history_path: Path, feature_id: str) -> dict:
    feature_path = ai_history_path / feature_id

    if not feature_path.exists():
        raise ValueError(f"Feature does not exist: {feature_id}")

    logger.debug(f"Getting status for feature {feature_id}")

    # Get worktree info
    worktree_info = None
    try:
        worktrees = list_worktrees(code_repo_path)
        feature_worktree = next((wt for wt in worktrees if wt.feature_id == feature_id), None)

        if feature_worktree:
            worktree_status = get_worktree_status(feature_worktree.path)
            worktree_info = {
                "path": feature_worktree.path,
                "branch": feature_worktree.branch,
                "is_clean": worktree_status.is_clean,
                "modified_files": worktree_status.modified_files,
                "untracked_files": worktree_status.untracked_files,
            }
            logger.debug(f"Found worktree at {feature_worktree.path}")
    except Exception as e:
        logger.warning(f"Could not get worktree info: {e}")

    # Get agent statuses
    agent_dirs = sorted(feature_path.iterdir())
    agents = []

    for agent_dir in agent_dirs:
        if not agent_dir.is_dir():
            continue

        agent_id = agent_dir.name
        in_dir = agent_dir / "in"
        out_dir = agent_dir / "out"

        pending = []
        completed = []

        if in_dir.exists():
            pending = list(in_dir.glob("*.md"))

        if out_dir.exists():
            completed = list(out_dir.glob("*.md"))

        # Get last activity
        last_activity = None
        all_files = pending + completed
        if all_files:
            latest_file = max(all_files, key=lambda f: f.stat().st_mtime)
            last_activity = datetime.fromtimestamp(latest_file.stat().st_mtime)

        agents.append(
            {
                "agent_id": agent_id,
                "pending_count": len(pending),
                "completed_count": len(completed),
                "last_activity": last_activity,
                "pending_files": pending,
                "completed_files": completed,
            }
        )

    logger.debug(f"Found {len(agents)} agents for feature {feature_id}")

    return {
        "feature_id": feature_id,
        "feature_path": feature_path,
        "worktree": worktree_info,
        "agents": agents,
    }


@click.command()
@click.argument("feature_id")
@click.option("--agent", help="Show details for specific agent")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed task lists")
def status_command(feature_id: str, agent: str | None, verbose: bool) -> None:
    settings = get_settings()

    try:
        status = get_feature_status(
            code_repo_path=settings.code_repo_path,
            ai_history_path=settings.ai_history_path,
            feature_id=feature_id,
        )

        # Header
        click.echo()
        click.echo(click.style(f"Feature: {status['feature_id']}", bold=True))
        click.echo(f"Path: {status['feature_path']}")
        click.echo()

        # Worktree status
        if status["worktree"]:
            wt = status["worktree"]
            click.echo(click.style("Worktree:", bold=True))
            click.echo(f"  Path:   {wt['path']}")
            click.echo(f"  Branch: {wt['branch']}")

            if wt["is_clean"]:
                click.echo(f"  Status: {click.style('Clean', fg='green')}")
            else:
                click.echo(f"  Status: {click.style('Dirty', fg='yellow')}")
                if verbose:
                    if wt["modified_files"]:
                        click.echo(f"  Modified: {', '.join(wt['modified_files'])}")
                    if wt["untracked_files"]:
                        click.echo(f"  Untracked: {', '.join(wt['untracked_files'])}")
            click.echo()
        else:
            click.echo(click.style("Worktree: Not found", fg="red"))
            click.echo()

        # Filter agents if specified
        agents = status["agents"]
        if agent:
            agents = [a for a in agents if a["agent_id"] == agent]
            if not agents:
                click.echo(click.style(f"✗ Agent not found: {agent}", fg="red"), err=True)
                raise click.Abort()

        # Agent status table
        click.echo(click.style("Agents:", bold=True))
        click.echo()

        # Table header
        click.echo(f"{'Agent':<20} {'Pending':<10} {'Completed':<12} {'Last Activity':<20}")
        click.echo("-" * 70)

        for agent_info in agents:
            agent_id = agent_info["agent_id"]
            pending = agent_info["pending_count"]
            completed = agent_info["completed_count"]
            last_activity = agent_info["last_activity"]

            # Color code pending count
            pending_str = click.style(str(pending), fg="yellow") if pending > 0 else str(pending)

            # Color code completed count
            if completed > 0:
                completed_str = click.style(str(completed), fg="green")
            else:
                completed_str = str(completed)

            # Format last activity
            activity_str = last_activity.strftime("%Y-%m-%d %H:%M:%S") if last_activity else "Never"

            click.echo(f"{agent_id:<20} {pending_str:<20} {completed_str:<22} {activity_str:<20}")

            # Show file lists if verbose
            if verbose:
                if agent_info["pending_files"]:
                    click.echo("  Pending:")
                    for f in agent_info["pending_files"]:
                        click.echo(f"    - {f.name}")

                if agent_info["completed_files"]:
                    click.echo("  Completed:")
                    for f in agent_info["completed_files"]:
                        click.echo(f"    - {f.name}")

                click.echo()

        click.echo()

        # Summary
        total_pending = sum(a["pending_count"] for a in agents)
        total_completed = sum(a["completed_count"] for a in agents)

        click.echo(f"Total: {total_pending} pending, {total_completed} completed")
        click.echo()

    except ValueError as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        raise click.Abort() from e
    except Exception as e:
        logger.exception("Unexpected error getting feature status")
        click.echo(click.style(f"✗ Unexpected error: {e}", fg="red"), err=True)
        raise click.Abort() from e


if __name__ == "__main__":
    status_command()
