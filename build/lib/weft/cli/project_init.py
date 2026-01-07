"""Project-level initialization command."""

from pathlib import Path

import click

from weft.config.project import create_default_weftrc
from weft.config.runtime import WeftRuntime
from weft.history.repo_manager import initialize_ai_history_repo


@click.command()
@click.option(
    "--project-name",
    prompt="Project name",
    help="Name of the project",
)
@click.option(
    "--project-type",
    type=click.Choice(["backend", "frontend", "fullstack"]),
    prompt="Project type",
    default="fullstack",
    help="Type of project (backend/frontend/fullstack)",
)
@click.option(
    "--ai-provider",
    type=click.Choice(["claude", "ollama", "other"]),
    prompt="AI provider",
    default="claude",
    help="AI provider to use (claude/ollama/other)",
)
@click.option(
    "--ai-history-path",
    type=click.Path(),
    prompt="AI history path",
    default="../weft-ai-history",
    help="Path to AI history repository",
)
@click.option(
    "--model",
    help="AI model to use (e.g., claude-3-5-sonnet-20241022)",
)
def project_init(
    project_name: str,
    project_type: str,
    ai_provider: str,
    ai_history_path: str,
    model: str | None,
) -> None:
    """Initialize a new Weft project.

    This is the first command to run in a new project. It creates:
    - .weftrc.yaml configuration file
    - .weft/ runtime directory structure
    - AI history repository (if specified)

    After initialization, run 'weft up' to start the runtime.
    """
    project_root = Path.cwd()

    # Check if already initialized
    weftrc_path = project_root / ".weftrc.yaml"
    weft_dir = project_root / ".weft"

    if weftrc_path.exists() or weft_dir.exists():
        click.echo("✓ Project already initialized.")
        click.echo(f"Found existing configuration at: {project_root}")
        click.echo("\n💡 Tip: Use 'weft feature create <name>' to start a new feature")
        return

    click.echo(f"\n🚀 Initializing Weft project: {project_name}")

    # 1. Create .weftrc.yaml
    click.echo("\n📝 Creating .weftrc.yaml...")

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

    click.echo("✓ Created .weftrc.yaml")

    # 2. Initialize .weft/ runtime directory
    click.echo("\n📁 Creating .weft/ directory structure...")
    runtime = WeftRuntime(root=project_root / ".weft")
    runtime.initialize()
    click.echo("✓ Created .weft/ directory")
    click.echo("  - features/")
    click.echo("  - tasks/in/, tasks/out/, tasks/processed/")
    click.echo("  - history/")
    click.echo("  - cache/")

    # 3. Initialize AI history repository
    ai_history_full_path = (project_root / ai_history_path).resolve()
    click.echo("\n📚 Initializing AI history repository...")

    if ai_history_full_path.exists():
        click.echo(f"⚠ AI history path already exists: {ai_history_full_path}")
    else:
        initialize_ai_history_repo(ai_history_full_path)
        click.echo(f"✓ Initialized AI history repository at {ai_history_full_path}")

    # 4. Print summary and next steps
    click.echo("\n" + "=" * 60)
    click.echo("✅ Weft project initialized successfully!")
    click.echo("=" * 60)

    click.echo(f"\nProject: {project_name}")
    click.echo(f"Type: {project_type}")
    click.echo(f"AI Provider: {ai_provider}")
    click.echo(f"Model: {model}")
    click.echo(f"AI History: {ai_history_full_path}")

    click.echo("\n📋 Next steps:")
    click.echo("  1. Run 'weft up' to start the docker runtime")
    click.echo("  2. Run 'weft feature create <name>' to start a feature")
    click.echo("\n💡 Tip: Edit .weftrc.yaml to customize agent settings\n")
