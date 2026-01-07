import logging
import re
from pathlib import Path
from typing import List, Optional

from weft.ai.backend import AIBackend
from weft.queue.models import PromptTask
from weft.watchers.base import BaseWatcher

logger = logging.getLogger(__name__)


class ArchitectWatcher(BaseWatcher):
    """Agent 01 Architect - Domain modeling and technical architecture.

    Receives prompts from Agent 00 Meta and designs technical architecture
    including domain models, use cases, API endpoints, and data flow.

    The Architect agent follows a security-first design approach, keeps solutions
    simple, and documents all architectural trade-offs.
    """

    def __init__(
        self,
        feature_id: str,
        agent_id: str,
        ai_history_path: Path,
        backend: AIBackend,
        prompt_spec_path: Optional[Path] = None,
        poll_interval: int = 2,
    ):
        super().__init__(feature_id, agent_id, ai_history_path, poll_interval)
        self.backend = backend

        if prompt_spec_path is None:
            prompt_spec_path = Path("prompt-specs/v1.0.0/01_architect.md")

        self.prompt_spec = self._load_prompt_spec(prompt_spec_path)
        self.spec_version = self._extract_spec_version(self.prompt_spec)

        logger.info(
            f"ArchitectWatcher initialized with spec version {self.spec_version} "
            f"for feature {feature_id}"
        )

    def _load_prompt_spec(self, spec_path: Path) -> str:
        if not spec_path.exists():
            raise FileNotFoundError(
                f"Prompt spec not found: {spec_path}. "
                f"Please ensure prompt specifications are created (STORY-4.3)."
            )

        logger.debug(f"Loading prompt spec from {spec_path}")
        return spec_path.read_text(encoding="utf-8")

    def _extract_spec_version(self, spec_content: str) -> str:
        match = re.search(r"\*\*Version:\*\*\s+(\d+\.\d+\.\d+)", spec_content)
        if match:
            version = match.group(1)
            logger.debug(f"Extracted spec version: {version}")
            return version

        logger.warning("Could not extract version from spec, using default 1.0.0")
        return "1.0.0"

    def process_prompt(self, prompt_task: PromptTask) -> str:
        architecture_request = prompt_task.prompt_text.strip()

        if not architecture_request:
            raise ValueError("Architecture request cannot be empty")

        logger.info(
            f"Processing architecture request: {architecture_request[:100]}..."
            if len(architecture_request) > 100
            else f"Processing architecture request: {architecture_request}"
        )

        architect_prompt = self._build_architect_prompt(architecture_request)

        logger.debug(f"Architect prompt length: {len(architect_prompt)} characters")

        output = self.backend.generate(architect_prompt)

        logger.info(f"Generated architecture: {len(output)} characters")

        self._validate_output(output)

        logger.info("Architecture output validated successfully")

        return output

    def _build_architect_prompt(self, architecture_request: str) -> str:
        return f"""You are Agent 01 Architect, responsible for domain modeling and technical architecture design.

Your role is defined by this specification:

{self.prompt_spec}

---

Agent 00 Meta has provided this architecture request:

{architecture_request}

---

Please design the technical architecture following the format specified in your role definition.

Your output MUST include these sections:
1. # Technical Design: [Feature Name]
2. ## Domain Model
3. ## Use Cases
4. ## API Requirements
5. ## Data Flow
6. ## Security Considerations
7. ## Scalability Considerations
8. ## Trade-offs & Decisions

Emphasize:
- Keep it simple - YAGNI principle
- Follow existing patterns in the system
- Security-first design (authentication, validation, encryption)
- Consider scalability (caching, indexes, async operations)
- Document all trade-offs and architectural decisions

Generate the technical architecture design now:"""

    def _validate_output(self, output: str) -> None:
        required_sections = [
            "## Domain Model",
            "## Use Cases",
            "## API Requirements",
            "## Data Flow",
            "## Trade-offs",
        ]

        missing_sections: List[str] = []
        for section in required_sections:
            if section not in output:
                missing_sections.append(section)

        if missing_sections:
            logger.error(
                f"Architecture output missing sections: {', '.join(missing_sections)}"
            )
            raise ValueError(
                f"Architecture output missing required sections: {', '.join(missing_sections)}. "
                f"Please ensure the AI backend generates complete output."
            )


def main():
    import sys

    from weft.ai.backend import create_backend_from_config
    from weft.config.settings import load_settings

    if len(sys.argv) < 2:
        print("Usage: python -m weft.agents.architect_agent <feature_id>")
        print()
        print("Example:")
        print("  python -m weft.agents.architect_agent feat/user-auth")
        print()
        print("Environment variables:")
        print("  WEFT_AI_HISTORY_PATH: Path to AI history repository (required)")
        print("  ANTHROPIC_API_KEY: Anthropic API key (required)")
        print("  WEFT_MODEL: Model to use (optional)")
        print("  WEFT_POLL_INTERVAL: Polling interval in seconds (optional, default: 2)")
        sys.exit(1)

    feature_id = sys.argv[1]

    try:
        settings = load_settings()
    except Exception as e:
        print(f"Error loading settings: {e}")
        print()
        print("Make sure environment variables are set:")
        print("  WEFT_CODE_REPO_PATH")
        print("  WEFT_AI_HISTORY_PATH")
        print("  ANTHROPIC_API_KEY")
        sys.exit(1)

    try:
        backend = create_backend_from_config()
    except Exception as e:
        print(f"Error creating AI backend: {e}")
        sys.exit(1)

    model_info = backend.get_model_info()
    print(f"Using AI backend: {model_info['backend']} ({model_info['model']})")

    try:
        watcher = ArchitectWatcher(
            feature_id=feature_id,
            agent_id="01-architect",
            ai_history_path=settings.ai_history_path,
            backend=backend,
            poll_interval=settings.poll_interval,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Make sure prompt specifications are created (STORY-4.3)")
        sys.exit(1)

    print(f"Starting Architect agent for feature: {feature_id}")
    print(f"Watching: {settings.ai_history_path}/{feature_id}/01-architect/in/")
    print(f"Poll interval: {settings.poll_interval}s")
    print("Press Ctrl+C to stop")
    print()

    try:
        watcher.start()
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        watcher.stop()
        print("Watcher stopped")


if __name__ == "__main__":
    main()
