"""Start feature development with agent orchestration."""

import time
from pathlib import Path
from typing import List, Optional

import click

from weft.config.project import load_weftrc
from weft.config.settings import get_settings
from weft.state import FeatureState, FeatureStatus, get_feature_state, get_state_file


class AgentOrchestrator:
    """Orchestrates agent execution in dependency order."""

    def __init__(self, feature_name: str, ai_history_path: Path, enabled_agents: List[str]):
        self.feature_name = feature_name
        self.ai_history_path = ai_history_path
        self.agents = enabled_agents

    def run(self, specific_agent: Optional[str] = None) -> bool:
        agents = [specific_agent] if specific_agent else self.agents

        for agent in agents:
            click.echo(f"\n🤖 Running Agent {agent}...")

            # Generate input for agent
            try:
                input_prompt = self._generate_agent_input(agent)
            except FileNotFoundError as e:
                click.echo(f"❌ Error: {e}", err=True)
                return False

            # Write to agent's input queue
            self._submit_to_agent(agent, input_prompt)

            # Wait for agent to complete
            success = self._wait_for_agent(agent)

            if not success:
                if not self._handle_agent_failure(agent):
                    return False  # User chose to abort
            else:
                click.echo(f"✓ Agent {agent} completed")

        return True

    def _generate_agent_input(self, agent: str) -> str:
        """Generate input prompt for agent based on spec and previous outputs.
        """
        if agent == "00-meta" or agent == "meta":
            # Meta gets feature description from spec
            return self._read_spec()
        elif agent == "01-architect" or agent == "architect":
            # Architect gets meta's output
            return self._read_agent_output("00-meta")
        elif agent == "02-openapi" or agent == "openapi":
            # OpenAPI gets architect's output
            return self._read_agent_output("01-architect")
        elif agent == "03-ui" or agent == "ui":
            # UI gets architect + openapi outputs
            architect_output = self._read_agent_output("01-architect")
            openapi_output = self._read_agent_output("02-openapi")
            return f"# 01-architect Output\n\n{architect_output}\n\n# 02-openapi Output\n\n{openapi_output}"
        elif agent == "04-integration" or agent == "integration":
            # Integration gets all previous outputs
            outputs = []
            for prev_agent in ["00-meta", "01-architect", "02-openapi", "03-ui"]:
                try:
                    output = self._read_agent_output(prev_agent)
                    outputs.append(f"# {prev_agent} Output\n\n{output}")
                except FileNotFoundError:
                    pass  # Skip if agent hasn't run
            return "\n\n".join(outputs)
        elif agent == "05-test" or agent == "test":
            # Test gets all outputs
            outputs = []
            for prev_agent in ["00-meta", "01-architect", "02-openapi", "03-ui", "04-integration"]:
                try:
                    output = self._read_agent_output(prev_agent)
                    outputs.append(f"# {prev_agent} Output\n\n{output}")
                except FileNotFoundError:
                    pass
            return "\n\n".join(outputs)
        else:
            # Unknown agent, just use spec
            return self._read_spec()

    def _read_spec(self) -> str:
        meta_out = self.ai_history_path / self.feature_name / "00-meta" / "out"
        if not meta_out.exists():
            raise FileNotFoundError(
                f"Spec not found at {meta_out}. Run 'weft feature-create {self.feature_name}' first."
            )

        results = list(meta_out.glob("*_result.md"))
        if not results:
            raise FileNotFoundError(
                f"No spec found in {meta_out}. Run 'weft feature-create {self.feature_name}' first."
            )

        # Get most recent result
        latest = max(results, key=lambda p: p.stat().st_mtime)
        return latest.read_text()

    def _read_agent_output(self, agent: str) -> str:
        output_dir = self.ai_history_path / self.feature_name / agent / "out"
        if not output_dir.exists():
            raise FileNotFoundError(f"Agent {agent} output not found at {output_dir}")

        results = list(output_dir.glob("*_result.md"))
        if not results:
            raise FileNotFoundError(f"No output found for agent {agent} in {output_dir}")

        # Get most recent result
        latest = max(results, key=lambda p: p.stat().st_mtime)
        return latest.read_text()

    def _submit_to_agent(self, agent: str, prompt: str) -> Path:
        input_dir = self.ai_history_path / self.feature_name / agent / "in"
        input_dir.mkdir(parents=True, exist_ok=True)

        prompt_file = input_dir / f"{self.feature_name}_prompt_v1.md"
        prompt_file.write_text(prompt)

        click.echo(f"  ✓ Submitted prompt: {prompt_file.name}")
        return prompt_file

    def _wait_for_agent(self, agent: str, timeout: int = 600) -> bool:
        output_dir = self.ai_history_path / self.feature_name / agent / "out"
        output_dir.mkdir(parents=True, exist_ok=True)

        start = time.time()

        with click.progressbar(
            length=timeout,
            label=f"  ⏳ Waiting for {agent}",
            show_eta=True,
        ) as bar:
            elapsed = 0
            while elapsed < timeout:
                results = list(output_dir.glob("*_result.md"))
                if results:
                    bar.update(timeout)  # Complete the bar
                    return True

                time.sleep(2)
                elapsed = int(time.time() - start)
                bar.update(min(2, timeout - elapsed))

        return False

    def _handle_agent_failure(self, agent: str) -> bool:
        click.echo(f"\n⚠ Agent {agent} failed or timed out.")
        click.echo("Possible issues:")
        click.echo("  • Runtime not started (run 'weft up')")
        click.echo(f"  • Agent {agent} watcher not running")
        click.echo("  • Agent processing taking longer than expected")

        choice = click.prompt(
            "\nWhat would you like to do?",
            type=click.Choice(["retry", "skip", "abort"]),
            default="retry",
            show_choices=True,
        )

        if choice == "retry":
            click.echo(f"\n🔄 Retrying agent {agent}...")
            return self._wait_for_agent(agent)
        elif choice == "skip":
            click.echo(f"⚠ Skipping agent {agent}")
            return True
        else:
            click.echo("❌ Aborting feature processing")
            return False


@click.command()
@click.argument("feature_name")
@click.option(
    "--agent",
    "-a",
    help="Run specific agent only (e.g., 'architect', '01-architect')",
)
def feature_start(feature_name: str, agent: Optional[str]) -> None:
    """Start automated agent pipeline for feature.

    Runs all enabled agents in sequence, or a specific agent if --agent flag is provided.
    Each agent receives context from previous agents' outputs.

    Agent Pipeline:
        00-meta → 01-architect → 02-openapi → 03-ui → 04-integration → 05-test

    Examples:
        weft feature start user-auth
        weft feature start user-auth --agent architect
        weft feature start dashboard -a 02-openapi
    """
    click.echo(f"\n🚀 Starting agent pipeline for feature: {feature_name}\n")

    # Load settings and config
    try:
        settings = get_settings()
    except ValueError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()

    ai_history_path = settings.ai_history_path

    # Validate feature state
    try:
        state = get_feature_state(feature_name)
        if state.status not in [FeatureStatus.DRAFT, FeatureStatus.IN_PROGRESS]:
            click.echo(
                f"❌ Error: Cannot start feature in '{state.status.value}' state",
                err=True,
            )
            click.echo(
                f"Feature must be in 'draft' or 'in-progress' state", err=True
            )
            click.echo(f"Current state: {state.status.value}", err=True)
            raise click.Abort()
        click.echo(f"✓ Feature state: {state.status.value}\n")
    except FileNotFoundError:
        click.echo(f"⚠ No state file found, creating initial state", err=True)
        state = FeatureState.create_initial(feature_name)
        state_file = get_state_file(feature_name)
        state.save(state_file)

    # Load config to get enabled agents
    config = load_weftrc()
    if not config:
        click.echo("❌ Error: .weftrc.yaml not found", err=True)
        click.echo("Run 'weft project-init' first to initialize the project", err=True)
        raise click.Abort()

    enabled_agents = config.agents.enabled
    if not enabled_agents:
        click.echo("❌ Error: No agents enabled in .weftrc.yaml", err=True)
        raise click.Abort()

    # Normalize agent name if specific agent requested
    if agent:
        # Support both "architect" and "01-architect" formats
        if not agent.startswith("0"):
            agent_map = {
                "meta": "00-meta",
                "architect": "01-architect",
                "openapi": "02-openapi",
                "ui": "03-ui",
                "integration": "04-integration",
                "test": "05-test",
            }
            agent = agent_map.get(agent, agent)

        # Verify agent is enabled
        if agent not in enabled_agents:
            click.echo(f"❌ Error: Agent '{agent}' is not enabled in .weftrc.yaml", err=True)
            click.echo(f"Enabled agents: {', '.join(enabled_agents)}", err=True)
            raise click.Abort()

        click.echo(f"Running single agent: {agent}")
    else:
        click.echo(f"Running pipeline: {' → '.join(enabled_agents)}")

    click.echo()

    # Create orchestrator and run
    orchestrator = AgentOrchestrator(
        feature_name=feature_name,
        ai_history_path=ai_history_path,
        enabled_agents=enabled_agents,
    )

    success = orchestrator.run(specific_agent=agent)

    if success:
        click.echo(f"\n✅ Feature '{feature_name}' processing complete!")

        # Transition state to READY (only if running full pipeline, not single agent)
        if not agent:
            try:
                state = get_feature_state(feature_name)
                if state.status == FeatureStatus.IN_PROGRESS:
                    state.transition_to(FeatureStatus.READY, "All agents completed successfully")
                    state_file = get_state_file(feature_name)
                    state.save(state_file)
                    click.echo(f"✓ Feature state: {state.status.value}")
            except Exception as e:
                click.echo(f"⚠ Could not update feature state: {e}", err=True)

        click.echo(f"\n📋 Next steps:")
        click.echo(f"  • Review outputs: {ai_history_path / feature_name}/")
        click.echo(f"  • Check status: weft status {feature_name}")
        click.echo(f"  • Accept changes: weft feature accept {feature_name}")
    else:
        click.echo(f"\n❌ Feature processing aborted")
        click.echo(f"Run command again to retry, or check logs with 'weft logs'")
        raise click.Abort()
