"""Project-level initialization command."""

import shutil
from pathlib import Path

import click

from weft.cli.utils import echo_separator
from weft.config.project import create_default_weftrc
from weft.config.runtime import WeftRuntime
from weft.history.repo_manager import initialize_ai_history_repo


def update_gitignore(project_root: Path) -> None:
    """Update .gitignore to exclude weft directories."""
    gitignore_path = project_root / ".gitignore"

    # Entries to add
    entries_to_add = [".weft/", "worktrees/"]

    # Read existing .gitignore
    if gitignore_path.exists():
        existing_content = gitignore_path.read_text()
        existing_lines = set(existing_content.strip().split("\n"))
    else:
        existing_content = ""
        existing_lines = set()

    # Check which entries need to be added
    new_entries = []
    for entry in entries_to_add:
        if entry not in existing_lines and entry.rstrip("/") not in existing_lines:
            new_entries.append(entry)

    # Add new entries if needed
    if new_entries:
        # Add newline before our section if file exists and doesn't end with newline
        if existing_content and not existing_content.endswith("\n"):
            existing_content += "\n"

        # Add comment header if we're adding to existing file
        if existing_content:
            existing_content += "\n# Weft AI workflow directories\n"
        else:
            existing_content = "# Weft AI workflow directories\n"

        # Add entries
        existing_content += "\n".join(new_entries) + "\n"

        # Write updated .gitignore
        gitignore_path.write_text(existing_content)


def copy_prompt_specs(dest_dir: Path) -> None:
    """Copy prompt specifications from weft package to project.

    Copies specs from the new nested agent structure where each agent
    has its own directory with specs/v1.0.0/{SPEC_FILENAME}.
    """
    # Get weft package directory
    weft_package_dir = Path(__file__).parent.parent
    agents_root_dir = weft_package_dir / "agents"

    if not agents_root_dir.exists():
        raise FileNotFoundError(f"Agents directory not found at: {agents_root_dir}")

    # Create versioned directory in project
    dest_version_dir = dest_dir / "v1.0.0"
    dest_version_dir.mkdir(parents=True, exist_ok=True)

    # Map agent directories to their spec filenames
    agent_spec_mapping = {
        "meta": "00_meta.md",
        "architect": "01_architect.md",
        "openapi": "02-openapi.md",
        "ui": "03-ui.md",
        "integration": "04-integration.md",
        "test": "05-test.md",
    }

    # Copy specs from nested agent structure
    import logging

    logger = logging.getLogger(__name__)
    for agent_name, spec_filename in agent_spec_mapping.items():
        # Source: agents/{agent_name}/specs/v1.0.0/{spec_filename}
        source_file = agents_root_dir / agent_name / "specs" / "v1.0.0" / spec_filename
        if source_file.exists():
            shutil.copy2(source_file, dest_version_dir / spec_filename)
            logger.debug(f"Copied spec: {agent_name} -> {spec_filename}")
        else:
            logger.warning(f"Spec not found: {source_file}")


@click.command()
@click.option(
    "--project-name",
    help="Name of the project (will prompt if not provided)",
)
@click.option(
    "--project-type",
    type=click.Choice(["backend", "frontend", "fullstack"]),
    help="Type of project",
)
@click.option(
    "--ai-provider",
    type=click.Choice(["claude", "ollama", "other"]),
    help="AI provider to use",
)
@click.option(
    "--ai-history-path",
    type=click.Path(),
    help="Path to AI history repository",
)
@click.option(
    "--model",
    help="AI model to use (e.g., claude-3-5-sonnet-20241022)",
)
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Re-initialize existing project (uses current config as defaults)",
)
def project_init(
    project_name: str | None,
    project_type: str | None,
    ai_provider: str | None,
    ai_history_path: str | None,
    model: str | None,
    force: bool,
) -> None:
    """Initialize a new Weft project.

    This is the first command to run in a new project. It creates:
    - .weftrc.yaml configuration file
    - .weft/ runtime directory structure
    - AI history repository (if specified)

    Use --force to re-initialize an existing project with new settings.

    After initialization, run 'weft up' to start the runtime.
    """
    project_root = Path.cwd()

    # Check if already initialized
    weftrc_path = project_root / ".weftrc.yaml"
    weft_dir = project_root / ".weft"
    existing_config = None

    if weftrc_path.exists() or weft_dir.exists():
        if not force:
            click.echo("✓ Project already initialized.")
            click.echo(f"Found existing configuration at: {project_root}")
            click.echo("\n💡 Tip: Use 'weft init --force' to re-initialize with new settings")
            click.echo("💡 Or use 'weft feature create <name>' to start a new feature")
            return

        # Load existing config to use as defaults
        from weft.config.project import load_weftrc

        existing_config = load_weftrc(weftrc_path)

        click.echo("🔄 Re-initializing Weft project (--force)")
        click.echo("Current configuration will be used as defaults...\n")

    # Determine defaults from existing config or use hardcoded defaults
    if existing_config:
        default_project_name = existing_config.project.name
        default_project_type = existing_config.project.type

        # Map internal provider back to user-friendly name
        reverse_provider_map = {
            "anthropic": "claude",
            "local": "ollama",
        }
        default_ai_provider = reverse_provider_map.get(existing_config.ai.provider, "claude")
        default_ai_history_path = existing_config.ai.history_path
        default_model = existing_config.ai.model
    else:
        default_project_name = None
        default_project_type = "fullstack"
        default_ai_provider = "claude"
        default_ai_history_path = "./weft-ai-history"
        default_model = None

    # Track if we're in interactive mode (any prompts shown)
    prompted_for_any = False

    # Prompt for missing parameters (with defaults from existing config if available)
    if not project_name:
        project_name = click.prompt(
            "Project name",
            default=default_project_name if default_project_name else Path.cwd().name,
        )
        prompted_for_any = True

    if not project_type:
        project_type = click.prompt(
            "Project type",
            type=click.Choice(["backend", "frontend", "fullstack"]),
            default=default_project_type,
        )
        prompted_for_any = True

    if not ai_provider:
        ai_provider = click.prompt(
            "AI provider",
            type=click.Choice(["claude", "ollama", "other"]),
            default=default_ai_provider,
        )
        prompted_for_any = True

    if not ai_history_path:
        ai_history_path = click.prompt(
            "AI history path",
            default=default_ai_history_path,
        )
        prompted_for_any = True

    # Only prompt for model if we're in interactive mode
    if not model and default_model and prompted_for_any:
        model = click.prompt(
            "AI model",
            default=default_model,
        )

    action = "Re-initializing" if force and existing_config else "Initializing"
    click.echo(f"\n🚀 {action} Weft project: {project_name}")

    # 1. Create .weftrc.yaml
    config_action = "Updating" if force and existing_config else "Creating"
    click.echo(f"\n📝 {config_action} .weftrc.yaml...")

    # Map user-friendly provider names to internal names
    provider_map = {
        "claude": "anthropic",
        "ollama": "local",
        "other": "local",
    }
    internal_provider = provider_map.get(ai_provider, ai_provider)

    # Determine default model based on provider
    if not model:
        if ai_provider == "claude":
            model = "claude-3-5-sonnet-20241022"
        elif ai_provider == "ollama":
            model = "llama2"
        else:
            model = "default"

    create_default_weftrc(
        project_root=project_root,
        project_name=project_name,
        project_type=project_type,
        ai_provider=internal_provider,
        model=model,
        ai_history_path=ai_history_path,
    )

    if force and existing_config:
        click.echo("✓ Updated .weftrc.yaml")
    else:
        click.echo("✓ Created .weftrc.yaml")

    # 2. Initialize .weft/ runtime directory
    weft_exists_before = weft_dir.exists()
    if weft_exists_before:
        click.echo("\n📁 Verifying .weft/ directory structure...")
    else:
        click.echo("\n📁 Creating .weft/ directory structure...")
    runtime = WeftRuntime(root=project_root / ".weft")
    runtime.initialize()
    if weft_exists_before:
        click.echo("✓ Verified .weft/ directory")
    else:
        click.echo("✓ Created .weft/ directory")
    click.echo("  - features/")
    click.echo("  - tasks/in/, tasks/out/, tasks/processed/")
    click.echo("  - history/")
    click.echo("  - cache/")
    click.echo("  - prompts/")

    # 2.5. Copy prompt specifications
    click.echo("\n📋 Copying agent prompt specifications...")
    try:
        copy_prompt_specs(project_root / ".weft" / "prompts")
        click.echo("✓ Copied prompt specs to .weft/prompts/v1.0.0/")
        click.echo("  - 00_meta.md")
        click.echo("  - 01_architect.md")
        click.echo("  - 02-openapi.md")
        click.echo("  - 03-ui.md")
        click.echo("  - 04-integration.md")
        click.echo("  - 05-test.md")
        click.echo("\n💡 Tip: Edit .weft/prompts/v1.0.0/*.md to customize agent behavior")
    except Exception as e:
        click.echo(f"⚠ Warning: Could not copy prompt specs: {e}", err=True)
        click.echo("Agents will use default specifications", err=True)

    # 3. Initialize AI history repository
    ai_history_full_path = (project_root / ai_history_path).resolve()
    click.echo("\n📚 Initializing AI history repository...")

    # Import validation function
    from weft.history.repo_manager import validate_ai_history_repo

    if ai_history_full_path.exists() and validate_ai_history_repo(ai_history_full_path):
        click.echo(f"✓ AI history repository already initialized: {ai_history_full_path}")
    else:
        if ai_history_full_path.exists():
            click.echo("  Directory exists but not a git repo, initializing...")
        initialize_ai_history_repo(ai_history_full_path)
        click.echo(f"✓ Initialized AI history repository at {ai_history_full_path}")

    # 3.5. Update .gitignore
    click.echo("\n🔒 Updating .gitignore...")
    try:
        update_gitignore(project_root)
        click.echo("✓ Updated .gitignore to exclude weft directories")
        click.echo("  - .weft/")
        click.echo("  - worktrees/")
    except Exception as e:
        click.echo(f"⚠ Warning: Could not update .gitignore: {e}", err=True)

    # 4. Print summary and next steps
    click.echo()
    echo_separator(width=60)
    if force and existing_config:
        click.echo("✅ Weft project re-initialized successfully!")
    else:
        click.echo("✅ Weft project initialized successfully!")
    echo_separator(width=60)

    click.echo(f"\nProject: {project_name}")
    click.echo(f"Type: {project_type}")
    click.echo(f"AI Provider: {ai_provider}")
    click.echo(f"Model: {model}")
    click.echo(f"AI History: {ai_history_full_path}")

    click.echo("\n📋 Next steps:")
    if force and existing_config:
        click.echo("  1. Review updated .weftrc.yaml")
        click.echo("  2. Restart runtime if running: 'weft down && weft up'")
        click.echo("  3. Continue with 'weft feature create <name>'")
    else:
        click.echo("  1. Run 'weft up' to start the docker runtime")
        click.echo("  2. Run 'weft feature create <name>' to start a feature")
    click.echo("\n💡 Tip: Edit .weftrc.yaml to customize agent settings\n")
