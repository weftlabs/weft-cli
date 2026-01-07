"""Start feature development with agent orchestration."""

import time
from pathlib import Path

import click

from weft.agents.orchestration import submit_prompt_to_agent, wait_for_agent_result
from weft.cli.utils import safe_get_settings
from weft.config.project import load_weftrc
from weft.constants import AGENT_IDS
from weft.state import FeatureState, FeatureStatus, get_feature_state, get_state_file


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


class AgentOrchestrator:
    """Orchestrates agent execution in dependency order."""

    def __init__(self, feature_name: str, ai_history_path: Path, enabled_agents: list[str]):
        self.feature_name = feature_name
        self.ai_history_path = ai_history_path
        self.agents = enabled_agents

    def run(self, specific_agent: str | None = None) -> bool:
        agents = [specific_agent] if specific_agent else self.agents

        for agent in agents:
            click.echo(f"\n🤖 Running Agent {agent}...")

            # Generate input for agent
            try:
                input_prompt = self._generate_agent_input(agent)
            except FileNotFoundError as e:
                click.echo(f"❌ Error: {e}", err=True)
                return False

            # Capture timestamp BEFORE submitting (for result tracking)
            submit_time = time.time()

            # Write to agent's input queue
            self._submit_to_agent(agent, input_prompt)

            # Wait for agent to complete (only accept new results)
            success = self._wait_for_agent(agent, min_timestamp=submit_time)

            if not success:
                if not self._handle_agent_failure(agent):
                    return False  # User chose to abort
            else:
                click.echo(f"✓ Agent {agent} completed")

        return True

    def _generate_agent_input(self, agent: str) -> str:
        """Generate input prompt for agent based on spec and previous outputs."""
        if agent == "00-meta" or agent == "meta":
            # Meta gets feature description from spec
            return self._read_spec()

        # All other agents get their specific prompt from Meta + previous outputs
        meta_output = self._read_agent_output("00-meta")
        agent_prompt = self._extract_agent_prompt_from_meta(meta_output, agent)

        # Add previous agent outputs as additional context
        if agent == "01-architect" or agent == "architect":
            # Architect gets just Meta's prompt (already has it)
            return agent_prompt
        elif agent == "02-openapi" or agent == "openapi":
            # OpenAPI gets Meta's prompt + Architect's output
            architect_output = self._read_agent_output("01-architect")
            return f"{agent_prompt}\n\n---\n\n# Previous Agent Output\n\n## Architect Design\n\n{architect_output}"
        elif agent == "03-ui" or agent == "ui":
            # UI gets Meta's prompt + Architect + OpenAPI outputs
            architect_output = self._read_agent_output("01-architect")
            openapi_output = self._read_agent_output("02-openapi")
            return f"{agent_prompt}\n\n---\n\n# Previous Agent Outputs\n\n## Architect Design\n\n{architect_output}\n\n## OpenAPI Specification\n\n{openapi_output}"
        elif agent == "04-integration" or agent == "integration":
            # Integration gets Meta's prompt + all previous outputs
            outputs = [agent_prompt, "\n---\n\n# Previous Agent Outputs\n"]
            for prev_agent in AGENT_IDS[1:4]:  # Architect, OpenAPI, UI
                try:
                    output = self._read_agent_output(prev_agent)
                    agent_name = prev_agent.split("-")[1].title()
                    outputs.append(f"\n## {agent_name}\n\n{output}")
                except FileNotFoundError:
                    pass
            return "\n".join(outputs)
        elif agent == "05-test" or agent == "test":
            # Test gets Meta's prompt + all previous outputs
            outputs = [agent_prompt, "\n---\n\n# Previous Agent Outputs\n"]
            for prev_agent in AGENT_IDS[1:5]:  # Architect, OpenAPI, UI, Integration
                try:
                    output = self._read_agent_output(prev_agent)
                    agent_name = prev_agent.split("-")[1].title()
                    outputs.append(f"\n## {agent_name}\n\n{output}")
                except FileNotFoundError:
                    pass
            return "\n".join(outputs)
        else:
            # Unknown agent, fallback to Meta's output
            return meta_output

    def _extract_agent_prompt_from_meta(self, meta_output: str, agent: str) -> str:
        """Extract the specific prompt section for an agent from Meta's output."""
        # Map agent IDs to section headers
        agent_map = {
            "01-architect": "For Agent 01 (Architect)",
            "architect": "For Agent 01 (Architect)",
            "02-openapi": "For Agent 02 (OpenAPI)",
            "openapi": "For Agent 02 (OpenAPI)",
            "03-ui": "For Agent 03 (UI)",
            "ui": "For Agent 03 (UI)",
            "04-integration": "For Agent 04 (Integration)",
            "integration": "For Agent 04 (Integration)",
            "05-test": "For Agent 05 (Test",
            "test": "For Agent 05 (Test",
        }

        section_header = agent_map.get(agent)
        if not section_header:
            # Fallback: return entire Meta output if agent not recognized
            return meta_output

        # Find the section for this agent
        lines = meta_output.split("\n")
        start_idx = None
        end_idx = len(lines)

        for i, line in enumerate(lines):
            # Look for "### For Agent XX"
            if section_header in line:
                start_idx = i
            # Stop at next agent section or horizontal rule
            elif start_idx is not None and (
                line.startswith("### For Agent") or line.strip() == "---"
            ):
                end_idx = i
                break

        if start_idx is None:
            # Section not found, return entire Meta output as fallback
            click.echo(
                f"⚠ Warning: Could not find '{section_header}' in Meta output, using full output",
                err=True,
            )
            return meta_output

        # Extract the section
        section_lines = lines[start_idx:end_idx]
        return "\n".join(section_lines).strip()

    def _read_spec(self) -> str:
        meta_out = self.ai_history_path / self.feature_name / AGENT_IDS[0] / "out"
        if not meta_out.exists():
            raise FileNotFoundError(
                f"Spec not found at {meta_out}. Run 'weft feature create {self.feature_name}' first."
            )

        results = list(meta_out.glob("*_result.md"))
        if not results:
            raise FileNotFoundError(
                f"No spec found in {meta_out}. Run 'weft feature create {self.feature_name}' first."
            )

        # Get most recent result
        latest = max(results, key=lambda p: p.stat().st_mtime)
        content = latest.read_text()
        return strip_yaml_frontmatter(content)

    def _read_agent_output(self, agent: str) -> str:
        output_dir = self.ai_history_path / self.feature_name / agent / "out"
        if not output_dir.exists():
            raise FileNotFoundError(f"Agent {agent} output not found at {output_dir}")

        results = list(output_dir.glob("*_result.md"))
        if not results:
            raise FileNotFoundError(f"No output found for agent {agent} in {output_dir}")

        # Get most recent result
        latest = max(results, key=lambda p: p.stat().st_mtime)
        content = latest.read_text()
        return strip_yaml_frontmatter(content)

    def _submit_to_agent(self, agent: str, prompt: str) -> Path:
        """Submit prompt to agent with proper YAML frontmatter."""
        prompt_file = submit_prompt_to_agent(
            feature_id=self.feature_name,
            agent_id=agent,
            prompt_content=prompt,
            ai_history_path=self.ai_history_path,
            revision=None,  # Use timestamp-based naming for pipeline runs
        )

        click.echo(f"  ✓ Submitted prompt: {prompt_file.name}")
        return prompt_file

    def _wait_for_agent(
        self, agent: str, timeout: int = 600, min_timestamp: float | None = None
    ) -> bool:
        result = wait_for_agent_result(
            feature_id=self.feature_name,
            agent_id=agent,
            ai_history_path=self.ai_history_path,
            timeout=timeout,
            min_timestamp=min_timestamp,
            show_progress=True,
        )

        return result is not None

    def _handle_agent_failure(self, agent: str) -> bool:
        click.echo(f"\n⚠ Agent {agent} failed or timed out.")
        click.echo("Possible issues:")
        click.echo("  • Runtime not started (run 'weft up')")
        click.echo(f"  • Agent {agent} watcher not running")
        click.echo("  • Agent processing taking longer than expected")
        click.echo(f"\n💡 Check logs: weft logs {agent}")
        click.echo(
            f"   Monitor output: tail -f {self.ai_history_path}/{self.feature_name}/{agent}/out/*.md"
        )

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
def feature_start(feature_name: str, agent: str | None) -> None:
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
    settings = safe_get_settings()
    ai_history_path = settings.ai_history_path

    # Validate feature state
    try:
        state = get_feature_state(feature_name)
        if state.status not in [
            FeatureStatus.DRAFT,
            FeatureStatus.IN_PROGRESS,
            FeatureStatus.READY,
        ]:
            click.echo(
                f"❌ Error: Cannot start feature in '{state.status.value}' state",
                err=True,
            )
            click.echo("Feature must be in 'draft', 'in-progress', or 'ready' state", err=True)
            click.echo(f"Current state: {state.status.value}", err=True)
            raise click.Abort()
        click.echo(f"✓ Feature state: {state.status.value}\n")

        # Transition READY -> IN_PROGRESS when re-running pipeline
        if state.status == FeatureStatus.READY and not agent:
            state.transition_to(FeatureStatus.IN_PROGRESS, "Re-running agent pipeline")
            state_file = get_state_file(feature_name)
            state.save(state_file)
            click.echo(f"✓ Transitioned to: {state.status.value}\n")
    except FileNotFoundError:
        click.echo("⚠ No state file found, creating initial state", err=True)
        state = FeatureState.create_initial(feature_name)
        state_file = get_state_file(feature_name)
        state.save(state_file)

    # Load config to get enabled agents
    config = load_weftrc()
    if not config:
        click.echo("❌ Error: .weftrc.yaml not found", err=True)
        click.echo("Run 'weft init' first to initialize the project", err=True)
        raise click.Abort()

    if not config.agents.enabled:
        click.echo("❌ Error: No agents enabled in .weftrc.yaml", err=True)
        raise click.Abort()

    # Normalize agent names to use prefixes (00-meta, 01-architect, etc.)
    agent_map = {
        "meta": AGENT_IDS[0],
        "architect": AGENT_IDS[1],
        "openapi": AGENT_IDS[2],
        "ui": AGENT_IDS[3],
        "integration": AGENT_IDS[4],
        "test": AGENT_IDS[5],
    }

    enabled_agents = [
        agent_map.get(a, a) if not a.startswith("0") else a for a in config.agents.enabled
    ]

    # Normalize agent name if specific agent requested
    if agent:
        # Support both "architect" and "01-architect" formats
        if not agent.startswith("0"):
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

        click.echo("\n📋 Next steps:")
        click.echo(f"  • Review outputs: weft feature review {feature_name}")
        click.echo(f"  • Check status: weft feature status {feature_name}")
    else:
        click.echo("\n❌ Feature processing aborted")
        click.echo("Run command again to retry, or check logs with 'weft logs'")
        raise click.Abort()
