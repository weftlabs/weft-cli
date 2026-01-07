"""Accept and merge completed features."""

import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
import yaml

from weft.config.project import load_weftrc
from weft.config.settings import get_settings
from weft.git.worktree import get_worktree_status, remove_worktree
from weft.state import FeatureStatus, get_feature_state, get_state_file


def update_ai_history_completion(feature_name: str, merge_commit: str, ai_history_path: Path) -> None:
    completion_file = ai_history_path / feature_name / "COMPLETED.md"

    completion_content = (
        f"# Feature Completed\n\n"
        f"Feature: {feature_name}\n"
        f"Merge Commit: {merge_commit}\n"
        f"Completed: {datetime.now().isoformat()}\n"
    )

    completion_file.write_text(completion_content)

    # Commit to AI history repo
    try:
        subprocess.run(
            ["git", "add", str(completion_file)],
            cwd=ai_history_path,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", f"Mark {feature_name} as completed (merge: {merge_commit[:8]})"],
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
    "--no-commit",
    is_flag=True,
    help="Fail if worktree is dirty (no auto-commit)",
)
@click.option(
    "--base-branch",
    default="main",
    help="Base branch to merge into (default: main)",
)
def feature_accept(feature_name: str, no_commit: bool, base_branch: str) -> None:
    """Accept and merge completed feature.

    Verifies the worktree is clean, merges changes to the base branch,
    and cleans up the feature worktree.

    Examples:
        weft feature accept user-auth
        weft feature accept dashboard --base-branch develop
        weft feature accept api-v2 --no-commit
    """
    click.echo(f"\n🎯 Accepting feature: {feature_name}\n")

    # Load settings and config
    try:
        settings = get_settings()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

    code_repo_path = settings.code_repo_path
    ai_history_path = settings.ai_history_path

    # Validate feature state
    try:
        state = get_feature_state(feature_name)
        if state.status != FeatureStatus.READY:
            click.echo(
                f"❌ Error: Cannot accept feature in '{state.status.value}' state",
                err=True,
            )
            click.echo(f"Feature must be in 'ready' state", err=True)
            if state.status == FeatureStatus.DRAFT:
                click.echo(f"Run 'weft feature start {feature_name}' first", err=True)
            elif state.status == FeatureStatus.IN_PROGRESS:
                click.echo(f"Wait for agents to complete, then run 'weft feature start {feature_name}' to finish", err=True)
            raise click.Abort()
        click.echo(f"✓ Feature state: {state.status.value}\n")
    except FileNotFoundError:
        click.echo(f"⚠ No state file found for feature, proceeding with caution", err=True)

    # Get worktree path
    worktree_path = code_repo_path.parent / "worktrees" / feature_name

    if not worktree_path.exists():
        click.echo(f"❌ Error: Worktree not found at {worktree_path}", err=True)
        click.echo(f"\n💡 Available features: weft feature-list", err=True)
        raise click.Abort()

    # 1. Check git status
    try:
        status = get_worktree_status(worktree_path)
    except Exception as e:
        click.echo(f"❌ Error checking worktree status: {e}", err=True)
        raise click.Abort()

    # 2. Handle dirty worktree
    if not status.is_clean:
        click.echo("⚠  Worktree has uncommitted changes:")

        if status.modified_files:
            click.echo("  Modified:")
            for f in status.modified_files:
                click.echo(f"    - {f}")

        if status.untracked_files:
            click.echo("  Untracked:")
            for f in status.untracked_files:
                click.echo(f"    - {f}")

        if no_commit:
            click.echo("\n❌ --no-commit flag requires clean worktree", err=True)
            raise click.Abort()

        if click.confirm("\nCommit changes?", default=True):
            commit_msg = click.prompt("Commit message")

            try:
                subprocess.run(
                    ["git", "add", "."],
                    cwd=worktree_path,
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "commit", "-m", commit_msg],
                    cwd=worktree_path,
                    check=True,
                    capture_output=True,
                )
                click.echo("✓ Changes committed\n")
            except subprocess.CalledProcessError as e:
                click.echo(f"❌ Error committing changes: {e}", err=True)
                raise click.Abort()
        else:
            click.echo("❌ Cannot accept feature with uncommitted changes", err=True)
            raise click.Abort()
    else:
        click.echo("✓ Worktree is clean\n")

    # 3. Merge to base branch
    branch_name = f"feature/{feature_name}"
    click.echo(f"📥 Merging {branch_name} to {base_branch}...")

    # Switch to base branch in main repo
    try:
        subprocess.run(
            ["git", "checkout", base_branch],
            cwd=code_repo_path,
            check=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Error switching to {base_branch}: {e}", err=True)
        raise click.Abort()

    # Merge with --no-ff to preserve feature branch history
    try:
        result = subprocess.run(
            ["git", "merge", branch_name, "--no-ff", "-m", f"Merge feature: {feature_name}"],
            cwd=code_repo_path,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
                click.echo("❌ Merge conflicts detected!", err=True)
                click.echo("\nPlease resolve conflicts manually:")
                click.echo(f"  1. Resolve conflicts in {base_branch}")
                click.echo("  2. Run 'git merge --continue'")
                click.echo(f"  3. Run 'weft feature-accept {feature_name}' again")
                raise click.Abort()
            else:
                click.echo(f"❌ Merge failed: {result.stderr}", err=True)
                raise click.Abort()

        click.echo(f"✓ Merged {branch_name} to {base_branch}\n")

    except subprocess.CalledProcessError as e:
        click.echo(f"❌ Error during merge: {e}", err=True)
        raise click.Abort()

    # 4. Get merge commit hash for audit trail
    try:
        merge_commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=code_repo_path,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except subprocess.CalledProcessError as e:
        click.echo(f"⚠  Warning: Could not get merge commit hash: {e}", err=True)
        merge_commit = "unknown"

    # 5. Update AI history with completion marker
    try:
        update_ai_history_completion(feature_name, merge_commit, ai_history_path)
        click.echo("✓ AI history updated with completion marker\n")
    except Exception as e:
        click.echo(f"⚠  Warning: Could not update AI history: {e}", err=True)

    # 6. Remove worktree
    click.echo("🧹 Cleaning up worktree...")
    try:
        remove_worktree(code_repo_path, feature_name, delete_branch=True)
        click.echo(f"✓ Removed worktree and branch {branch_name}\n")
    except Exception as e:
        click.echo(f"⚠  Warning: Could not remove worktree: {e}", err=True)
        click.echo("You may need to remove it manually.\n")

    # 7. Update feature state to COMPLETED
    try:
        state = get_feature_state(feature_name)
        state.merge_commit = merge_commit
        state.transition_to(FeatureStatus.COMPLETED, f"Merged to {base_branch}")
        state_file = get_state_file(feature_name)
        state.save(state_file)
        click.echo(f"✓ Feature state: {state.status.value}\n")
    except Exception as e:
        click.echo(f"⚠  Warning: Could not update feature state: {e}", err=True)

    # 8. Success message
    click.echo(f"✅ Feature '{feature_name}' accepted and merged!")
    click.echo(f"   Merge commit: {merge_commit[:8]}")
    click.echo(f"   AI history: {ai_history_path / feature_name}/")
    click.echo()
