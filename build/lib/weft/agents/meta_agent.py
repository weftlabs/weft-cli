"""Agent 00 Meta - Feature understanding and prompt generation."""

import logging
import re
from pathlib import Path
from typing import Optional

from weft.ai.backend import AIBackend
from weft.queue.models import PromptTask
from weft.watchers.base import BaseWatcher

logger = logging.getLogger(__name__)


class MetaWatcher(BaseWatcher):
    """Agent 00 Meta - Feature understanding and prompt generation.

    Reads feature requirements and generates structured prompts
    for downstream agents (starting with Agent 01 Architect).

    The Meta agent loads its behavior from a versioned prompt specification
    and uses an AI backend (e.g., Claude) to analyze feature requests and
    generate detailed prompts for other agents.
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
            prompt_spec_path = Path("prompt-specs/v1.0.0/00_meta.md")

        self.prompt_spec = self._load_prompt_spec(prompt_spec_path)
        self.spec_version = self._extract_spec_version(self.prompt_spec)

        logger.info(
            f"MetaWatcher initialized with spec version {self.spec_version} "
            f"for feature {feature_id}"
        )

    def _load_prompt_spec(self, spec_path: Path) -> str:
        if not spec_path.exists():
            raise FileNotFoundError(
                f"Prompt spec not found: {spec_path}. "
                f"Please ensure prompt specifications are created (STORY-4.2)."
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
        feature_description = prompt_task.prompt_text.strip()

        if not feature_description:
            raise ValueError("Feature description cannot be empty")

        logger.info(
            f"Processing feature request: {feature_description[:100]}..."
            if len(feature_description) > 100
            else f"Processing feature request: {feature_description}"
        )

        meta_prompt = self._build_meta_prompt(feature_description)

        logger.debug(f"Meta-prompt length: {len(meta_prompt)} characters")

        output = self.backend.generate(meta_prompt)

        logger.info(f"Generated output: {len(output)} characters")

        return output

    def _build_meta_prompt(self, feature_description: str) -> str:
        return f"""You are Agent 00 Meta, responsible for feature understanding and prompt generation.

Your role is defined by this specification:

{self.prompt_spec}

---

The user has submitted this feature request:

{feature_description}

---

Please analyze this feature and generate a structured prompt for Agent 01 (Architect).

Your output should follow the format specified in your role definition above.
Include:
- Clear objective for the architect
- Key requirements extracted from the feature description
- Any constraints or considerations
- Expected deliverables

Generate the prompt for Agent 01 now:"""


def main():
    import sys

    from weft.ai.backend import create_backend_from_config
    from weft.config.settings import load_settings

    if len(sys.argv) < 2:
        print("Usage: python -m weft.agents.meta_agent <feature_id>")
        print()
        print("Example:")
        print("  python -m weft.agents.meta_agent feat/user-auth")
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
        watcher = MetaWatcher(
            feature_id=feature_id,
            agent_id="00-meta",
            ai_history_path=settings.ai_history_path,
            backend=backend,
            poll_interval=settings.poll_interval,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Make sure prompt specifications are created (STORY-4.2)")
        sys.exit(1)

    print(f"Starting Meta agent for feature: {feature_id}")
    print(f"Watching: {settings.ai_history_path}/{feature_id}/00-meta/in/")
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
