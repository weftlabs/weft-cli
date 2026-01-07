"""Drop/delete a feature without merging."""

import click

from weft.cli.feature.review import handle_drop
from weft.cli.utils import safe_get_settings
from weft.git.worktree import get_worktree_path


@click.command()
@click.argument("feature_name")
@click.option(
    "--delete-history",
    is_flag=True,
    help="Delete AI history (default: preserve for audit)",
)
@click.option(
    "--reason",
    "-r",
    help="Reason for dropping (for audit trail)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Skip confirmation prompt",
)
def feature_drop(
    feature_name: str,
    delete_history: bool,
    reason: str | None,
    force: bool,
) -> None:
    """Drop/abandon a feature without merging.

    This removes the feature worktree, branch, and optionally the AI history.
    By default, AI history is preserved for audit purposes.

    Examples:

        # Drop a feature you created but never started
        weft feature drop my-feature

        # Drop and delete all AI history
        weft feature drop my-feature --delete-history

        # Drop with a reason (for audit trail)
        weft feature drop my-feature -r "Requirements changed"

        # Skip confirmation (be careful!)
        weft feature drop my-feature --force

    Note: By default, AI history is marked as DROPPED but preserved
    for audit compliance. Use --delete-history to permanently remove it.
    """
    settings = safe_get_settings()

    # Get paths
    code_repo_path = settings.code_repo_path
    ai_history_path = settings.ai_history_path

    # If force flag is set, skip the confirmation in handle_drop
    # by temporarily patching click.confirm
    try:
        worktree_path = get_worktree_path(code_repo_path, feature_name)

        if force:
            from unittest.mock import patch

            import click as click_module

            with patch.object(click_module, "confirm", return_value=True):
                handle_drop(
                    feature_name,
                    code_repo_path,
                    ai_history_path,
                    worktree_path,
                    delete_history,
                    reason,
                )
        else:
            handle_drop(
                feature_name,
                code_repo_path,
                ai_history_path,
                worktree_path,
                delete_history,
                reason,
            )
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort() from e
