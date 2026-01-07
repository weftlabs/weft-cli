"""List and display feature information."""

from datetime import datetime, timedelta

import click
from tabulate import tabulate

from weft.cli.utils import safe_get_settings
from weft.constants import FEATURE_STATE_ORDER
from weft.git.worktree import list_worktrees
from weft.state import get_feature_state


def humanize_time(dt: datetime) -> str:
    """Convert datetime to human-readable string."""
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
    settings = safe_get_settings()
    code_repo_path = settings.code_repo_path

    # Get all worktrees
    try:
        worktrees = list_worktrees(code_repo_path)
    except Exception as e:
        click.echo(f"❌ Error listing worktrees: {e}", err=True)
        raise click.Abort() from e

    # Filter to only feature branches
    feature_worktrees = [
        wt for wt in worktrees if wt.branch.startswith("feature/") or wt.branch.startswith("feat/")
    ]

    # Build feature list from worktrees
    features_dict = {}  # Use dict to avoid duplicates
    for wt in feature_worktrees:
        # Extract feature name from branch
        feature_name = wt.branch.replace("feature/", "").replace("feat/", "")

        # Get state
        try:
            state = get_feature_state(feature_name)
        except FileNotFoundError:
            # No state file - feature not initialized properly
            continue

        # Filter by status
        if not all and state.status.value in ["completed", "dropped"]:
            continue

        features_dict[feature_name] = {
            "name": feature_name,
            "branch": wt.branch,
            "status": state.status.value,
            "activity": state.last_activity,
            "path": str(wt.path),
            "has_worktree": True,
        }

    # If --all, also scan for state files (to include dropped features without worktrees)
    if all:
        features_dir = code_repo_path / ".weft" / "features"
        if features_dir.exists():
            for feature_dir in features_dir.iterdir():
                if not feature_dir.is_dir():
                    continue

                feature_name = feature_dir.name

                # Skip if already in list from worktrees
                if feature_name in features_dict:
                    continue

                # Try to load state
                try:
                    state = get_feature_state(feature_name)
                except FileNotFoundError:
                    continue

                features_dict[feature_name] = {
                    "name": feature_name,
                    "branch": f"feature/{feature_name}",
                    "status": state.status.value,
                    "activity": state.last_activity,
                    "path": "N/A",
                    "has_worktree": False,
                }

    features = list(features_dict.values())

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
        features.sort(key=lambda f: FEATURE_STATE_ORDER.get(f["status"], 99))  # type: ignore[arg-type]
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
        }.get(
            f["status"], "❓"  # type: ignore[arg-type]
        )

        # Show branch or indicate no worktree
        if f.get("has_worktree", True):
            branch_display = f["branch"]
        else:
            branch_display = f"{f['branch']} (no worktree)"

        table_data.append(
            [
                f["name"],
                branch_display,
                f"{status_icon} {f['status']}",
                humanize_time(f["activity"]),  # type: ignore[arg-type]
            ]
        )

    headers = ["Feature", "Branch", "Status", "Last Activity"]
    click.echo(tabulate(table_data, headers=headers, tablefmt="simple"))

    # Summary
    click.echo(f"\n✓ Total: {len(features)} feature{'s' if len(features) != 1 else ''}")

    if not all:
        click.echo("  (Use --all to show completed/dropped features)")

    click.echo()
