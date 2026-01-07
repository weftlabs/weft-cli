"""Submit tasks to agent queues."""

import logging
from pathlib import Path
from typing import Optional

import click

from weft.config.settings import get_settings
from weft.queue.file_ops import write_prompt
from weft.queue.models import PromptTask

logger = logging.getLogger(__name__)

VALID_AGENTS = [
    "00-meta",
    "01-architect",
    "02-openapi",
    "03-ui",
    "04-integration",
    "05-test",
]


def validate_agent_id(agent_id: str) -> bool:
    """Validate agent ID.
    """
    if agent_id not in VALID_AGENTS:
        raise ValueError(
            f"Invalid agent ID: {agent_id}. "
            f"Valid agents: {', '.join(VALID_AGENTS)}"
        )
    return True


def validate_feature_exists(ai_history_path: Path, feature_id: str) -> bool:
    """Check if feature exists in AI history.
    """
    feature_path = ai_history_path / feature_id
    if not feature_path.exists():
        raise ValueError(
            f"Feature does not exist: {feature_id}. "
            f"Run 'weft init {feature_id}' first."
        )
    return True


@click.command()
@click.argument("feature_id")
@click.argument("agent_id")
@click.argument("prompt", required=False)
@click.option(
    "--file", "-f", type=click.Path(exists=True), help="Read prompt from file"
)
@click.option(
    "--spec-version",
    default="1.0.0",
    help="Prompt specification version (default: 1.0.0)",
)
@click.option(
    "--revision", default=1, type=int, help="Prompt revision number (default: 1)"
)
def submit_command(
    feature_id: str,
    agent_id: str,
    prompt: Optional[str],
    file: Optional[str],
    spec_version: str,
    revision: int,
):
    """Submit a prompt to an agent.

    Submits a prompt to the specified agent's input queue for processing.

    Examples:

        # Submit inline prompt
        weft submit feat-123 00-meta "Add user authentication"

        # Submit from file
        weft submit feat-123 01-architect --file architecture.md

        # Submit with specific spec version
        weft submit feat-456 00-meta "Add payment" --spec-version 1.1.0
    """
    settings = get_settings()

    try:
        # Validate inputs
        validate_agent_id(agent_id)
        validate_feature_exists(settings.ai_history_path, feature_id)

        # Get prompt text
        if file:
            prompt_text = Path(file).read_text()
            logger.info(f"Read prompt from file: {file}")
        elif prompt:
            prompt_text = prompt
        else:
            raise ValueError("Either provide a prompt or use --file option")

        if not prompt_text.strip():
            raise ValueError("Prompt cannot be empty")

        logger.info(
            f"Submitting prompt to {agent_id} for feature {feature_id} "
            f"(spec={spec_version}, rev={revision})"
        )

        # Create prompt task
        prompt_task = PromptTask(
            feature_id=feature_id,
            agent_id=agent_id,
            prompt_text=prompt_text,
            spec_version=spec_version,
            revision=revision,
        )

        # Write to queue
        prompt_file_path = write_prompt(
            ai_history_path=settings.ai_history_path,
            feature_id=feature_id,
            agent_id=agent_id,
            prompt_task=prompt_task,
        )

        logger.info(f"Prompt written to {prompt_file_path}")

        # Success message
        click.echo()
        click.echo(click.style("✓ Prompt submitted successfully!", fg="green"))
        click.echo()
        click.echo(f"  Feature:       {feature_id}")
        click.echo(f"  Agent:         {agent_id}")
        click.echo(f"  Prompt file:   {prompt_file_path}")
        click.echo(f"  Spec version:  {spec_version}")
        click.echo(f"  Revision:      {revision}")
        click.echo()
        click.echo(f"The agent will process this prompt when running.")
        click.echo(f"To start the agent: weft watch {feature_id} {agent_id}")

    except ValueError as e:
        click.echo(click.style(f"✗ Error: {e}", fg="red"), err=True)
        raise click.Abort()
    except Exception as e:
        logger.exception("Unexpected error during prompt submission")
        click.echo(click.style(f"✗ Unexpected error: {e}", fg="red"), err=True)
        raise click.Abort()


if __name__ == "__main__":
    submit_command()
