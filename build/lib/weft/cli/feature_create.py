"""Create and orchestrate new features with AI agents."""

import time
from pathlib import Path
from typing import Optional

import click

from weft.cli.init import initialize_feature
from weft.config.project import load_weftrc
from weft.config.settings import get_settings
from weft.state import FeatureState, FeatureStatus, get_state_file


def wait_for_agent_output(
    agent: str,
    feature_id: str,
    ai_history_path: Path,
    timeout: int = 300,
) -> Optional[str]:
    """Wait for agent to produce output file.
    """
    output_dir = ai_history_path / feature_id / agent / "out"

    if not output_dir.exists():
        return None

    start = time.time()
    with click.progressbar(
        length=timeout,
        label=f"⏳ Waiting for Agent {agent}",
        show_eta=True,
    ) as bar:
        elapsed = 0
        while elapsed < timeout:
            # Check for *_result.md files
            results = list(output_dir.glob("*_result.md"))
            if results:
                # Get most recent result
                latest = max(results, key=lambda p: p.stat().st_mtime)
                bar.update(timeout)  # Complete the bar
                return latest.read_text()

            time.sleep(2)
            elapsed = int(time.time() - start)
            bar.update(min(2, timeout - elapsed))

    return None


def display_spec(spec_content: str) -> None:
    click.echo("\n" + "=" * 70)
    click.echo("FEATURE SPECIFICATION")
    click.echo("=" * 70)
    click.echo(spec_content)
    click.echo("=" * 70 + "\n")


def submit_to_agent(
    feature_id: str,
    agent: str,
    prompt_content: str,
    ai_history_path: Path,
    revision: int = 1,
) -> Path:
    """Submit prompt to agent's input queue.
    """
    input_dir = ai_history_path / feature_id / agent / "in"
    input_dir.mkdir(parents=True, exist_ok=True)

    prompt_file = input_dir / f"{feature_id}_prompt_v{revision}.md"
    prompt_file.write_text(prompt_content)

    return prompt_file


@click.command()
@click.argument("feature_name")
@click.option(
    "--description",
    "-d",
    help="Initial feature description (if not provided, will prompt)",
)
@click.option(
    "--base-branch",
    default="main",
    help="Base branch for feature (default: main)",
)
def feature_create(
    feature_name: str,
    description: Optional[str],
    base_branch: str,
) -> None:
    """Create a new feature with Agent 00 interactive loop.

    Creates git worktree, AI history structure, and interactively works
    with Agent 00 (Meta) to produce an accepted spec.md.

    The workflow:
    1. Create worktree and history structure
    2. Submit feature description to Agent 00
    3. Wait for Agent 00 to generate spec
    4. Display spec and ask for acceptance
    5. If user wants to iterate, refine and repeat
    6. Mark spec as approved when accepted

    Examples:
        weft feature create user-auth
        weft feature create user-auth -d "Add JWT authentication"
        weft feature create dashboard --base-branch develop
    """
    click.echo(f"\n🚀 Creating feature: {feature_name}\n")

    # Load settings
    try:
        settings = get_settings()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

    code_repo_path = settings.code_repo_path
    ai_history_path = settings.ai_history_path

    # Check if feature already exists
    worktree_path = code_repo_path.parent / f"worktrees/{feature_name}"
    feature_history_path = ai_history_path / feature_name

    if worktree_path.exists() or feature_history_path.exists():
        click.echo(f"⚠ Feature '{feature_name}' already exists")
        click.echo(f"  Worktree: {worktree_path}")
        click.echo(f"  History: {feature_history_path}")

        if not click.confirm("Resume with existing feature?", default=True):
            click.echo("Cancelled.")
            raise click.Abort()

        # Check for existing spec
        meta_out = feature_history_path / "00-meta" / "out"
        if meta_out.exists():
            results = list(meta_out.glob("*_result.md"))
            if results:
                click.echo(f"\n✓ Found existing spec (v{len(results)})")
                latest_spec = max(results, key=lambda p: p.stat().st_mtime)
                spec_content = latest_spec.read_text()
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
                    return

                # Fall through to iteration loop
                revision = len(results) + 1
                description = click.prompt(
                    "\nWhat would you like to change in the spec?"
                )
            else:
                revision = 1
        else:
            revision = 1
    else:
        # Create new feature
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
        except Exception as e:
            click.echo(f"❌ Error creating feature: {e}", err=True)
            raise click.Abort()

        revision = 1

    # Get initial description if not provided
    if not description:
        description = click.prompt("Feature description")

    # Interactive loop with Agent 00
    accepted = False

    while not accepted:
        click.echo(f"\n📤 Submitting to Agent 00 (v{revision})...")

        # Submit to Agent 00
        prompt_file = submit_to_agent(
            feature_id=feature_name,
            agent="00-meta",
            prompt_content=description,
            ai_history_path=ai_history_path,
            revision=revision,
        )
        click.echo(f"✓ Created prompt: {prompt_file.name}")

        # Wait for Agent 00 to process
        click.echo("\n⏳ Waiting for Agent 00 to generate spec...")
        click.echo("(This may take 1-2 minutes. Agent must be running via 'weft up')\n")

        result = wait_for_agent_output(
            agent="00-meta",
            feature_id=feature_name,
            ai_history_path=ai_history_path,
            timeout=300,
        )

        if not result:
            click.echo("\n⚠ Timeout waiting for Agent 00", err=True)
            click.echo("Possible issues:", err=True)
            click.echo("  • Runtime not started (run 'weft up')", err=True)
            click.echo("  • Agent 00 watcher not running", err=True)
            click.echo("  • Agent processing taking longer than expected", err=True)

            if not click.confirm("\nRetry waiting?", default=True):
                click.echo("\n💡 You can manually check:")
                click.echo(f"   {feature_history_path / '00-meta' / 'out'}/")
                click.echo("\nRun this command again to resume when ready.")
                raise click.Abort()

            # Retry wait
            result = wait_for_agent_output(
                agent="00-meta",
                feature_id=feature_name,
                ai_history_path=ai_history_path,
                timeout=300,
            )

            if not result:
                click.echo("\n❌ Still no response from Agent 00", err=True)
                raise click.Abort()

        # Display spec to user
        click.echo("\n✨ Agent 00 has generated the specification!")
        display_spec(result)

        # Prompt for acceptance
        choice = click.prompt(
            "Accept this spec?",
            type=click.Choice(["yes", "no", "iterate"]),
            default="yes",
            show_choices=True,
        )

        if choice == "yes":
            accepted = True
            click.echo("\n✅ Feature spec accepted!")

            # Transition state to IN_PROGRESS
            state_file = get_state_file(feature_name)
            try:
                state = FeatureState.load(state_file)
                state.transition_to(FeatureStatus.IN_PROGRESS, "Spec approved by user")
                state.save(state_file)
                click.echo(f"✓ Feature state: {state.status.value}")
            except Exception as e:
                click.echo(f"⚠ Could not update feature state: {e}", err=True)

            click.echo(f"\nNext: Run 'weft feature start {feature_name}' to run agents")

        elif choice == "no":
            click.echo("\n❌ Feature creation cancelled")
            click.echo(f"Worktree and history preserved at:")
            click.echo(f"  • {worktree_path}")
            click.echo(f"  • {feature_history_path}")
            raise click.Abort()

        else:  # iterate
            refinement = click.prompt("\nWhat would you like to change?")
            description = f"{description}\n\nRefinement: {refinement}"
            revision += 1
            click.echo(f"\n🔄 Starting iteration v{revision}...")
