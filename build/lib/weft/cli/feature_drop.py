"""Drop and clean up features."""

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from weft.config.settings import get_settings
from weft.git.worktree import remove_worktree
from weft.state import FeatureStatus, get_feature_state, get_state_file


def mark_ai_history_dropped(
    feature_name: str, ai_history_path: Path, reason: Optional[str] = None
) -> None:
    drop_file = ai_history_path / feature_name / "DROPPED.md"

    content = (
        f"# Feature Dropped\n\n"
        f"Feature: {feature_name}\n"
        f"Dropped: {datetime.now().isoformat()}\n"
    )
    if reason:
        content += f"Reason: {reason}\n"

    drop_file.write_text(content)

    # Commit to AI history repo
    try:
        subprocess.run(
            ["git", "add", str(drop_file)],
            cwd=ai_history_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [
                "git",
                "commit",
                "-m",
                f"Mark {feature_name} as dropped: {reason or 'No reason provided'}",
            ],
            cwd=ai_history_path,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError:
        # AI history might not be a git repo, that's okay
        pass


@click.command()
@click.argument("feature_name")
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
@click.option(
    "--delete-history",
    is_flag=True,
    help="Delete AI history (default: preserve for audit)",
)
@click.option(
    "--reason",
    "-r",
    help="Reason for dropping feature (for audit trail)",
)
def feature_drop(
    feature_name: str,
    force: bool,
    delete_history: bool,
    reason: Optional[str],
) -> None:
    """Drop (discard) a feature without merging.

    Removes the worktree and feature branch. By default, preserves AI
    history for audit trail.

    Examples:
        weft feature drop bad-idea
        weft feature drop experiment --force --delete-history
        weft feature drop prototype --reason "Approach didn't work"
    """
    click.echo(f"\n🗑️  Dropping feature: {feature_name}\n")

    # Load settings
    try:
        settings = get_settings()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

    code_repo_path = settings.code_repo_path
    ai_history_path = settings.ai_history_path

    # Validate feature state (can't drop terminal states)
    try:
        state = get_feature_state(feature_name)
        if state.status in [FeatureStatus.COMPLETED, FeatureStatus.DROPPED]:
            click.echo(
                f"❌ Error: Cannot drop feature in terminal state '{state.status.value}'",
                err=True,
            )
            click.echo(f"Feature already {state.status.value}", err=True)
            raise click.Abort()
        click.echo(f"✓ Current feature state: {state.status.value}\n")
    except FileNotFoundError:
        click.echo(f"⚠ No state file found for feature", err=True)

    # Get worktree path
    worktree_path = code_repo_path.parent / "worktrees" / feature_name

    if not worktree_path.exists():
        click.echo(f"❌ Error: Worktree not found at {worktree_path}", err=True)
        click.echo(f"\n💡 Available features: weft feature-list", err=True)
        raise click.Abort()

    # 1. Confirm with user (unless --force)
    if not force:
        click.echo(f"⚠️  WARNING: This will permanently delete feature '{feature_name}'")
        click.echo("\nThe following will be removed:")
        click.echo(f"  - Worktree directory: {worktree_path}")
        click.echo(f"  - Feature branch: feature/{feature_name}")

        if delete_history:
            click.echo(f"  - AI history directory: {ai_history_path / feature_name}")
        else:
            click.echo(f"  ✓ AI history will be preserved for audit")

        click.echo()
        confirmation = click.prompt("Type the feature name to confirm", type=str)

        if confirmation != feature_name:
            click.echo("\n❌ Confirmation failed. Feature not dropped.", err=True)
            raise click.Abort()

        click.echo()

    # 2. Remove worktree and branch
    click.echo("🧹 Removing worktree and branch...")
    try:
        remove_worktree(code_repo_path, feature_name, delete_branch=True)
        click.echo(f"✓ Removed worktree and branch feature/{feature_name}\n")
    except Exception as e:
        click.echo(f"⚠️  Warning: Could not remove worktree: {e}", err=True)
        click.echo("Continuing with cleanup...\n")

    # 3. Handle AI history
    feature_history = ai_history_path / feature_name

    if feature_history.exists():
        if delete_history:
            click.echo("🗑️  Deleting AI history...")
            try:
                shutil.rmtree(feature_history)
                click.echo(f"✓ Deleted AI history directory\n")

                # Commit deletion to AI history repo
                try:
                    subprocess.run(
                        ["git", "add", "-A"],
                        cwd=ai_history_path,
                        check=True,
                        capture_output=True,
                    )
                    subprocess.run(
                        [
                            "git",
                            "commit",
                            "-m",
                            f"Delete AI history for dropped feature: {feature_name}",
                        ],
                        cwd=ai_history_path,
                        check=True,
                        capture_output=True,
                    )
                except subprocess.CalledProcessError:
                    pass  # Not a git repo or commit failed, that's okay
            except Exception as e:
                click.echo(f"⚠️  Warning: Could not delete AI history: {e}", err=True)
        else:
            # Preserve with drop marker
            try:
                mark_ai_history_dropped(feature_name, ai_history_path, reason)
                click.echo(f"✓ AI history preserved with drop marker\n")
            except Exception as e:
                click.echo(f"⚠️  Warning: Could not mark AI history: {e}", err=True)
    else:
        click.echo("ℹ️  No AI history found for this feature\n")

    # 4. Update feature state to DROPPED
    try:
        state = get_feature_state(feature_name)
        state.drop_reason = reason
        state.transition_to(FeatureStatus.DROPPED, reason or "Feature dropped")
        state_file = get_state_file(feature_name)
        state.save(state_file)
        click.echo(f"✓ Feature state: {state.status.value}\n")
    except Exception as e:
        click.echo(f"⚠️  Warning: Could not update feature state: {e}", err=True)

    # 5. Success message
    click.echo(f"✅ Feature '{feature_name}' dropped")
    if reason:
        click.echo(f"   Reason: {reason}")
    if not delete_history:
        click.echo(f"   AI history: {ai_history_path / feature_name}/")
    click.echo()
