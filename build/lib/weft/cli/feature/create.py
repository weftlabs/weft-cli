"""Create and orchestrate new features with AI agents."""

import time

import click

from weft.agents.orchestration import submit_prompt_to_agent, wait_for_agent_result
from weft.cli.feature.helpers import initialize_feature
from weft.cli.utils import echo_section_start, safe_get_settings
from weft.constants import AGENT_IDS, DEFAULT_BASE_BRANCH, DEFAULT_TIMEOUT
from weft.git.worktree import get_worktree_path
from weft.state import FeatureState, FeatureStatus, get_state_file, load_feature_state


def strip_yaml_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from markdown content."""
    lines = content.split("\n")
    if not lines or lines[0].strip() != "---":
        return content

    # Find the closing ---
    try:
        end_idx = lines[1:].index("---") + 1
        # Return everything after the closing ---
        return "\n".join(lines[end_idx + 1 :]).lstrip()
    except ValueError:
        # No closing ---, return as is
        return content


def display_spec(spec_content: str) -> None:
    echo_section_start("FEATURE SPECIFICATION")
    click.echo(spec_content)
    click.echo("=" * 70 + "\n")


def _check_existing_feature(
    feature_name: str, feature_history_path
) -> tuple[bool, int, str | None]:
    """Check if feature exists and handle resume logic."""
    meta_out = feature_history_path / AGENT_IDS[0] / "out"
    if not meta_out.exists():
        return True, 1, None

    results = list(meta_out.glob("*_result.md"))
    if not results:
        return True, 1, None

    click.echo(f"\n✓ Found existing spec (v{len(results)})")
    latest_spec = max(results, key=lambda p: p.stat().st_mtime)
    spec_content = strip_yaml_frontmatter(latest_spec.read_text())
    display_spec(spec_content)

    action = click.prompt(
        "What would you like to do?",
        type=click.Choice(["accept", "iterate", "cancel"]),
        default="iterate",
    )

    if action == "cancel":
        click.echo("Cancelled.")
        raise click.Abort()
    elif action == "accept":
        click.echo("\n✅ Feature spec accepted!")
        click.echo(f"\nNext: Run 'weft feature start {feature_name}' to run agents")
        return False, 0, None

    # iterate
    revision = len(results) + 1
    description = click.prompt("\nWhat would you like to change in the spec?")
    return True, revision, description


def _create_new_feature(
    feature_name: str,
    code_repo_path,
    ai_history_path,
    base_branch: str,
    worktree_path,
    feature_history_path,
) -> None:
    """Create worktree and AI history structure."""
    click.echo("📁 Creating worktree and AI history structure...")

    try:
        initialize_feature(
            feature_id=feature_name,
            code_repo_path=code_repo_path,
            ai_history_path=ai_history_path,
            base_branch=base_branch,
        )
        click.echo(f"✓ Created worktree: {worktree_path}")
        click.echo(f"✓ Created AI history: {feature_history_path}")

        # Initialize feature state
        state = FeatureState.create_initial(feature_name)
        state_file = get_state_file(feature_name)
        state.save(state_file)
        click.echo(f"✓ Initialized feature state: {state.status.value}\n")
    except ValueError as e:
        click.echo(f"\n❌ {e}\n", err=True)
        raise click.Abort() from e
    except Exception as e:
        click.echo(f"\n❌ Error creating feature: {e}\n", err=True)
        raise click.Abort() from e


def _submit_and_wait_for_spec(
    feature_name: str, description: str, ai_history_path, revision: int
) -> tuple[str | None, float]:
    """Submit prompt to Agent 00 and wait for result."""
    click.echo(f"\n📤 Submitting to Agent 00 (v{revision})...")

    submit_time = time.time()

    prompt_file = submit_prompt_to_agent(
        feature_id=feature_name,
        agent_id=AGENT_IDS[0],
        prompt_content=description,
        ai_history_path=ai_history_path,
        revision=revision,
    )
    click.echo(f"✓ Created prompt: {prompt_file.name}")

    click.echo("\n⏳ Waiting for Agent 00 to generate spec...")
    click.echo("(This may take 1-2 minutes. Agent must be running via 'weft up')\n")

    result = wait_for_agent_result(
        feature_id=feature_name,
        agent_id=AGENT_IDS[0],
        ai_history_path=ai_history_path,
        timeout=DEFAULT_TIMEOUT,
        min_timestamp=submit_time,
    )

    return result, submit_time


def _retry_wait_for_spec(
    feature_name: str, ai_history_path, feature_history_path, submit_time: float
) -> str | None:
    """Handle retry logic when Agent 00 times out."""
    click.echo("\n⚠ Timeout waiting for Agent 00", err=True)
    click.echo("Possible issues:", err=True)
    click.echo("  • Runtime not started (run 'weft up')", err=True)
    click.echo("  • Agent 00 watcher not running", err=True)
    click.echo("  • Agent processing taking longer than expected", err=True)

    if not click.confirm("\nRetry waiting?", default=True):
        click.echo("\n💡 You can manually check:")
        click.echo(f"   {feature_history_path / AGENT_IDS[0] / 'out'}/")
        click.echo("\nRun this command again to resume when ready.")
        raise click.Abort()

    result = wait_for_agent_result(
        feature_id=feature_name,
        agent_id=AGENT_IDS[0],
        ai_history_path=ai_history_path,
        timeout=DEFAULT_TIMEOUT,
        min_timestamp=submit_time,
    )

    if not result:
        click.echo("\n❌ Still no response from Agent 00", err=True)
        raise click.Abort()

    return result


def _handle_spec_acceptance(feature_name: str, spec_content: str) -> tuple[bool, str | None]:
    """Display spec and get user acceptance decision."""
    click.echo("\n✨ Agent 00 has generated the specification!")
    display_spec(strip_yaml_frontmatter(spec_content))

    choice = click.prompt(
        "Accept this spec?",
        type=click.Choice(["yes", "no", "iterate"]),
        default="yes",
        show_choices=True,
    )

    if choice == "yes":
        click.echo("\n✅ Feature spec accepted!")

        try:
            state = load_feature_state(feature_name)
            state.transition_to(FeatureStatus.IN_PROGRESS, "Spec approved by user")
            state_file = get_state_file(feature_name)
            state.save(state_file)
            click.echo(f"✓ Feature state: {state.status.value}")
        except Exception as e:
            click.echo(f"⚠ Could not update feature state: {e}", err=True)

        click.echo(f"\nNext: Run 'weft feature start {feature_name}' to run agents")
        return True, None

    elif choice == "no":
        click.echo("\n❌ Feature creation cancelled")
        return False, None

    else:  # iterate
        refinement = click.prompt("\nWhat would you like to change?")
        return False, refinement


@click.command()
@click.argument("feature_name")
@click.option(
    "--description",
    "-d",
    help="Initial feature description (if not provided, will prompt)",
)
@click.option(
    "--base-branch",
    default=DEFAULT_BASE_BRANCH,
    help=f"Base branch for feature (default: {DEFAULT_BASE_BRANCH})",
)
def feature_create(
    feature_name: str,
    description: str | None,
    base_branch: str,
) -> None:
    """Create a new feature with Agent 00 interactive loop.

    Examples:
        weft feature create user-auth
        weft feature create user-auth -d "Add JWT authentication"
    """
    click.echo(f"\n🚀 Creating feature: {feature_name}\n")

    # Load settings
    settings = safe_get_settings()
    code_repo_path = settings.code_repo_path
    ai_history_path = settings.ai_history_path

    worktree_path = get_worktree_path(code_repo_path, feature_name)
    feature_history_path = ai_history_path / feature_name

    # Check if feature was previously dropped
    dropped_marker = feature_history_path / "DROPPED.md"
    if dropped_marker.exists():
        click.echo(f"⚠ Feature '{feature_name}' was previously dropped")
        if not click.confirm("Re-create feature with same name?", default=True):
            click.echo("Cancelled.")
            raise click.Abort()
        # Remove dropped marker to allow re-creation
        dropped_marker.unlink()

    # Check if feature already exists
    if worktree_path.exists() or feature_history_path.exists():
        click.echo(f"⚠ Feature '{feature_name}' already exists")
        click.echo(f"  Worktree: {worktree_path}")
        click.echo(f"  History: {feature_history_path}")

        if not click.confirm("Resume with existing feature?", default=True):
            click.echo("Cancelled.")
            raise click.Abort()

        should_continue, revision, description = _check_existing_feature(
            feature_name, feature_history_path
        )
        if not should_continue:
            return
    else:
        _create_new_feature(
            feature_name,
            code_repo_path,
            ai_history_path,
            base_branch,
            worktree_path,
            feature_history_path,
        )
        revision = 1

    # Get initial description if not provided
    if not description:
        description = click.prompt("Feature description")

    # Interactive loop with Agent 00
    while True:
        result, submit_time = _submit_and_wait_for_spec(
            feature_name, description, ai_history_path, revision
        )

        if not result:
            result = _retry_wait_for_spec(
                feature_name, ai_history_path, feature_history_path, submit_time
            )

        accepted, refinement = _handle_spec_acceptance(feature_name, result)

        if accepted:
            break
        elif refinement is None:
            # User chose "no" - cancelled
            click.echo("Worktree and history preserved at:")
            click.echo(f"  • {worktree_path}")
            click.echo(f"  • {feature_history_path}")
            raise click.Abort()
        else:
            # User chose "iterate"
            description = f"{description}\n\nRefinement: {refinement}"
            revision += 1
            click.echo(f"\n🔄 Starting iteration v{revision}...")
