"""List and display feature information."""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional

import click
import yaml
from pydantic import BaseModel
from tabulate import tabulate

from weft.config.settings import get_settings
from weft.git.worktree import list_worktrees


class FeatureState(BaseModel):
    """Feature state model."""

    status: str = "draft"
    last_activity: datetime


def get_feature_state(feature_name: str, ai_history_path: Path) -> FeatureState:
    # Check for state file in .weft/features/{feature}/state.yaml (Story 8.13)
    # For now, derive state from AI history
    feature_dir = ai_history_path / feature_name

    if not feature_dir.exists():
        # Feature has no history yet
        return FeatureState(status="draft", last_activity=datetime.now())

    # Check for spec approval (00-meta output exists)
    meta_out = feature_dir / "00-meta" / "out"
    if not meta_out.exists() or not list(meta_out.glob("*_result.md")):
        return FeatureState(status="draft", last_activity=datetime.now())

    # Get last activity from most recent agent output
    last_activity = None
    status = "in-progress"  # Default if we have spec

    # Check all agent output directories
    for agent_dir in feature_dir.iterdir():
        if not agent_dir.is_dir():
            continue

        out_dir = agent_dir / "out"
        if not out_dir.exists():
            continue

        results = list(out_dir.glob("*_result.md"))
        if results:
            for result in results:
                mtime = datetime.fromtimestamp(result.stat().st_mtime)
                if last_activity is None or mtime > last_activity:
                    last_activity = mtime

    # If we have outputs from all enabled agents, mark as ready
    # For now, simplified: if we have any outputs, mark in-progress
    if last_activity is None:
        last_activity = datetime.now()

    return FeatureState(status=status, last_activity=last_activity)


def humanize_time(dt: datetime) -> str:
    """Convert datetime to human-readable string.
    """
    now = datetime.now()
    delta = now - dt

    if delta < timedelta(minutes=1):
        return "just now"
    elif delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes}m ago"
    elif delta < timedelta(hours=24):
        hours = int(delta.total_seconds() / 3600)
        return f"{hours}h ago"
    elif delta < timedelta(days=2):
        return "yesterday"
    elif delta < timedelta(days=7):
        days = delta.days
        return f"{days}d ago"
    else:
        return dt.strftime("%Y-%m-%d")


@click.command()
@click.option(
    "--all",
    "-a",
    is_flag=True,
    help="Show completed and dropped features",
)
@click.option(
    "--sort-by",
    type=click.Choice(["name", "status", "activity"]),
    default="activity",
    help="Sort by name, status, or activity (default: activity)",
)
def feature_list(all: bool, sort_by: str) -> None:
    """List all features with their status.

    Shows all active features (draft, in-progress, ready) by default.
    Use --all to include completed and dropped features.

    Examples:
        weft feature list
        weft feature list --all
        weft feature list --sort-by name
    """
    click.echo("\n📋 Features\n")

    # Load settings
    try:
        settings = get_settings()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

    code_repo_path = settings.code_repo_path
    ai_history_path = settings.ai_history_path

    # Get all worktrees
    try:
        worktrees = list_worktrees(code_repo_path)
    except Exception as e:
        click.echo(f"❌ Error listing worktrees: {e}", err=True)
        raise click.Abort()

    # Filter to only feature branches
    feature_worktrees = [
        wt for wt in worktrees if wt.branch.startswith("feature/") or wt.branch.startswith("feat/")
    ]

    if not feature_worktrees:
        click.echo("No features found.")
        click.echo("\n💡 Create a new feature with: weft feature-create <name>\n")
        return

    # Get state for each feature
    features = []
    for wt in feature_worktrees:
        # Extract feature name from branch
        feature_name = wt.branch.replace("feature/", "").replace("feat/", "")

        # Get state
        state = get_feature_state(feature_name, ai_history_path)

        # Filter by status
        if not all and state.status in ["completed", "dropped"]:
            continue

        features.append(
            {
                "name": feature_name,
                "branch": wt.branch,
                "status": state.status,
                "activity": state.last_activity,
                "path": str(wt.path),
            }
        )

    if not features:
        if all:
            click.echo("No features found.")
        else:
            click.echo("No active features found.")
            click.echo("\n💡 Use --all to show completed/dropped features\n")
        return

    # Sort
    if sort_by == "name":
        features.sort(key=lambda f: f["name"])
    elif sort_by == "status":
        status_order = {
            "in-progress": 0,
            "draft": 1,
            "ready": 2,
            "completed": 3,
            "dropped": 4,
        }
        features.sort(key=lambda f: status_order.get(f["status"], 99))
    else:  # activity
        features.sort(key=lambda f: f["activity"], reverse=True)

    # Format table
    table_data = []
    for f in features:
        status_icon = {
            "draft": "📝",
            "in-progress": "⏳",
            "ready": "✅",
            "completed": "✔",
            "dropped": "❌",
        }.get(f["status"], "❓")

        table_data.append(
            [
                f["name"],
                f["branch"],
                f"{status_icon} {f['status']}",
                humanize_time(f["activity"]),
            ]
        )

    headers = ["Feature", "Branch", "Status", "Last Activity"]
    click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))

    # Summary
    click.echo(f"\n✓ Total: {len(features)} feature{'s' if len(features) != 1 else ''}")

    if not all:
        click.echo("  (Use --all to show completed/dropped features)")

    click.echo()
