"""Base class for agents that use versioned prompt specifications."""

import logging
import re
from pathlib import Path

import yaml

from weft.ai.backend import AIBackend
from weft.queue.models import PromptTask
from weft.watchers.base import BaseWatcher

logger = logging.getLogger(__name__)


class BaseSpecAgent(BaseWatcher):
    """Config-driven agent that loads behavior from YAML config and markdown spec.

    Each agent is defined by:
    - config.yaml: metadata (agent_id, stage, order, validation rules)
    - specs/v1.0.0/*.md: behavior specification

    No subclassing needed - agents are pure data configuration.
    """

    def __init__(
        self,
        feature_id: str,
        agent_id: str,
        ai_history_path: Path,
        backend: AIBackend,
        agent_dir: Path | None = None,
        config: dict | None = None,
        prompt_spec_path: Path | None = None,
        poll_interval: int = 2,
    ):
        super().__init__(feature_id, agent_id, ai_history_path, poll_interval)
        self.backend = backend

        # Load config
        if config is None:
            if agent_dir is None:
                agent_dir = self._resolve_agent_dir(agent_id)
            config = self._load_config(agent_dir)

        self.config = config
        self.agent_name = config["agent_name"]
        self.stage = config["stage"]
        self.order_in_stage = config["order_in_stage"]
        self.description = config.get("description", "")
        self.validation_rules = config.get("validation", {})

        # Load spec
        if prompt_spec_path is None:
            prompt_spec_path = self._resolve_spec_path()

        self.prompt_spec = self._load_prompt_spec(prompt_spec_path)
        self.spec_version = self._extract_spec_version(self.prompt_spec)

        logger.info(
            f"Agent '{self.agent_name}' initialized (stage: {self.stage}, "
            f"spec version: {self.spec_version}) for feature {feature_id}"
        )

    def _resolve_agent_dir(self, agent_id: str) -> Path:
        # Extract agent name from agent_id (e.g., "00-meta" -> "meta")
        agent_name = agent_id.split("-", 1)[-1] if "-" in agent_id else agent_id
        agent_dir = Path(__file__).parent / agent_name

        if not agent_dir.exists():
            raise FileNotFoundError(f"Agent directory not found: {agent_dir}")

        return agent_dir

    def _load_config(self, agent_dir: Path) -> dict:
        config_path = agent_dir / "config.yaml"

        if not config_path.exists():
            raise FileNotFoundError(
                f"Agent config not found: {config_path}. "
                f"Each agent must have a config.yaml file."
            )

        with open(config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        logger.debug(f"Loaded config from {config_path}")
        return config

    def _resolve_spec_path(self) -> Path:
        """Tries project-local override first, falls back to package default."""
        spec_filename = self.config["spec_filename"]
        agent_name = self.config["agent_name"]

        # 1. Check project-local spec (highest priority)
        local_spec = Path(f".weft/prompts/v1.0.0/{spec_filename}")
        if local_spec.exists():
            logger.debug(f"Using project-local spec: {local_spec}")
            return local_spec

        # 2. Check package nested agent structure (default)
        package_spec = Path(__file__).parent / agent_name / "specs" / "v1.0.0" / spec_filename
        if package_spec.exists():
            logger.debug(f"Using package spec: {package_spec}")
            return package_spec

        # No spec found - return expected path for clear error message
        return package_spec

    def _load_prompt_spec(self, spec_path: Path) -> str:
        if not spec_path.exists():
            raise FileNotFoundError(
                f"Prompt spec not found: {spec_path}. "
                f"Please ensure the spec file exists in the agent directory."
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
        prompt_text = prompt_task.prompt_text.strip()

        if not prompt_text:
            raise ValueError("Prompt text cannot be empty")

        logger.info(
            f"Processing prompt: {prompt_text[:100]}..."
            if len(prompt_text) > 100
            else f"Processing prompt: {prompt_text}"
        )

        # Build the complete prompt from spec + input
        full_prompt = self._build_prompt(prompt_text)

        logger.debug(f"Full prompt length: {len(full_prompt)} characters")

        # Load conversation history if conversation_id is provided
        conversation_history = None
        if prompt_task.conversation_id:
            conversation_history = self._load_conversation_history(prompt_task.conversation_id)
            logger.info(
                f"Loaded conversation history: {len(conversation_history)} message(s) "
                f"for conversation_id={prompt_task.conversation_id}"
            )

        # Generate output using AI backend with conversation context
        output = self.backend.generate(full_prompt, conversation_history)

        logger.info(f"Generated output: {len(output)} characters")

        # Validate output if validation rules exist
        if self.validation_rules.get("required_sections"):
            self._validate_output(output)
            logger.info("Output validation passed")

        return output

    def _load_conversation_history(self, conversation_id: str) -> list[dict]:
        """Returns messages array formatted for Claude API, sorted chronologically."""
        messages = []

        # Read previous prompts with matching conversation_id
        in_dir = self.agent_dir / "in"
        out_dir = self.agent_dir / "out"

        if not in_dir.exists() or not out_dir.exists():
            return messages

        # Collect prompt/result pairs
        pairs = []

        # Read all .processed prompts
        for prompt_file in sorted(in_dir.glob("*.processed")):
            try:
                content = prompt_file.read_text(encoding="utf-8")
                # Parse frontmatter to get conversation_id
                if "---" not in content:
                    continue

                parts = content.split("---", 2)
                if len(parts) < 3:
                    continue

                import yaml

                frontmatter = yaml.safe_load(parts[1])
                if not isinstance(frontmatter, dict):
                    continue

                # Check if conversation_id matches
                if frontmatter.get("conversation_id") != conversation_id:
                    continue

                # Extract prompt text
                prompt_text = parts[2].strip()

                # Get timestamp from filename or file creation time
                timestamp = prompt_file.stat().st_ctime

                # Find matching result file (by conversation_id first, then timestamp)
                result_file = self._find_matching_result(out_dir, timestamp, conversation_id)

                if result_file:
                    result_content = result_file.read_text(encoding="utf-8")
                    # Extract result text (after frontmatter)
                    if "---" in result_content:
                        result_parts = result_content.split("---", 2)
                        if len(result_parts) >= 3:
                            result_text = result_parts[2].strip()
                        else:
                            result_text = result_content
                    else:
                        result_text = result_content

                    pairs.append(
                        {
                            "timestamp": timestamp,
                            "prompt": prompt_text,
                            "result": result_text,
                        }
                    )

            except Exception as e:
                logger.warning(f"Failed to load conversation history from {prompt_file}: {e}")
                continue

        # Sort pairs by timestamp
        pairs.sort(key=lambda x: x["timestamp"])

        # Build messages array
        for pair in pairs:
            messages.append({"role": "user", "content": pair["prompt"]})
            messages.append({"role": "assistant", "content": pair["result"]})

        return messages

    def _find_matching_result(
        self, out_dir: Path, prompt_timestamp: float, conversation_id: str | None = None
    ) -> Path | None:
        """Matches result files by conversation_id first, then timestamp as fallback."""
        # Try UUID-based matching first if conversation_id is provided
        if conversation_id:
            for result_file in out_dir.glob("*_result.md"):
                try:
                    content = result_file.read_text(encoding="utf-8")
                    # Parse frontmatter to check conversation_id
                    if "---" not in content:
                        continue

                    parts = content.split("---", 2)
                    if len(parts) < 3:
                        continue

                    import yaml

                    frontmatter = yaml.safe_load(parts[1])
                    if (
                        isinstance(frontmatter, dict)
                        and frontmatter.get("conversation_id") == conversation_id
                    ):
                        return result_file
                except Exception:
                    # Skip files that can't be parsed
                    continue

        # Fall back to timestamp-based matching (legacy support)
        tolerance = 60  # seconds
        for result_file in out_dir.glob("*_result.md"):
            result_timestamp = result_file.stat().st_ctime
            if abs(result_timestamp - prompt_timestamp) <= tolerance:
                return result_file

        return None

    def _build_prompt(self, prompt_text: str) -> str:
        """Agents are differentiated by spec content, not code."""
        return f"""You are {self.agent_name} agent, responsible for {self.description}.

Your role and behavior are defined by this specification:

{self.prompt_spec}

---

You have received this input:

{prompt_text}

---

Please process this input according to your role specification above.
Generate output that follows the format and requirements specified in your role definition."""

    def _validate_output(self, output: str) -> None:
        required_sections = self.validation_rules.get("required_sections", [])

        if not required_sections:
            return

        missing_sections = []
        for section in required_sections:
            if section not in output:
                missing_sections.append(section)

        if missing_sections:
            logger.error(f"Output missing required sections: {', '.join(missing_sections)}")
            raise ValueError(
                f"Output missing required sections: {', '.join(missing_sections)}. "
                f"Please ensure the AI backend generates complete output."
            )
