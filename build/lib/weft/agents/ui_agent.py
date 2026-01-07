"""Agent 03 UI - UI/UX skeleton generation from architecture and APIs.

The UI agent receives architecture from Agent 01 and API specs from Agent 02,
then generates comprehensive UI skeletal structures with components, routing,
state management, and accessibility considerations.
"""

import logging
import re
from pathlib import Path
from typing import Optional

from weft.ai.backend import AIBackend
from weft.queue.models import PromptTask
from weft.watchers.base import BaseWatcher

logger = logging.getLogger(__name__)


class UIWatcher(BaseWatcher):
    """Agent 03 UI - UI/UX skeleton generation.

    Receives architecture from Agent 01 Architect and API specs from Agent 02 OpenAPI,
    then generates comprehensive UI skeletal structures including component hierarchy,
    routing, layouts, state management strategy, and accessibility considerations.

    The UI agent follows component-based architecture, responsive design principles,
    and accessibility best practices.
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
            prompt_spec_path = Path("prompt-specs/v1.0.0/03-ui.md")

        self.prompt_spec = self._load_prompt_spec(prompt_spec_path)
        self.spec_version = self._extract_spec_version(self.prompt_spec)

        logger.info(
            f"UIWatcher initialized with spec version {self.spec_version} "
            f"for feature {feature_id}"
        )

    def _load_prompt_spec(self, spec_path: Path) -> str:
        if not spec_path.exists():
            raise FileNotFoundError(
                f"Prompt spec not found: {spec_path}. "
                f"Please ensure prompt specification file exists."
            )

        logger.debug(f"Loading prompt spec from {spec_path}")
        return spec_path.read_text(encoding="utf-8")

    def _extract_spec_version(self, spec_content: str) -> str:
        match = re.search(r"Prompt Specification Version:\s+(\d+\.\d+\.\d+)", spec_content)
        if match:
            version = match.group(1)
            logger.debug(f"Extracted spec version: {version}")
            return version

        logger.warning("Could not extract version from spec, using default 1.0.0")
        return "1.0.0"

    def process_prompt(self, prompt_task: PromptTask) -> str:
        feature_requirements = prompt_task.prompt_text.strip()

        if not feature_requirements:
            raise ValueError("Feature requirements cannot be empty")

        logger.info(
            f"Processing UI skeleton generation request: {feature_requirements[:100]}..."
            if len(feature_requirements) > 100
            else f"Processing UI skeleton generation request: {feature_requirements}"
        )

        architect_output = self._read_previous_agent_output("01-architect")
        openapi_output = self._read_previous_agent_output("02-openapi")

        logger.debug(f"Architect output length: {len(architect_output)} characters")
        logger.debug(f"OpenAPI output length: {len(openapi_output)} characters")

        ui_prompt = self._build_ui_prompt(
            feature_requirements, architect_output, openapi_output
        )

        logger.debug(f"UI prompt length: {len(ui_prompt)} characters")

        output = self.backend.generate(ui_prompt)

        logger.info(f"Generated UI skeleton: {len(output)} characters")

        self._validate_output(output)

        logger.info("UI skeleton validated successfully")

        return output

    def _read_previous_agent_output(self, agent_id: str) -> str:
        agent_output_dir = self.ai_history_path / self.feature_id / agent_id / "out"

        if not agent_output_dir.exists():
            raise FileNotFoundError(
                f"Output directory not found for agent {agent_id}: {agent_output_dir}"
            )

        result_files = sorted(
            agent_output_dir.glob("*_result.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not result_files:
            raise FileNotFoundError(
                f"No output files found for agent {agent_id} in {agent_output_dir}"
            )

        latest_file = result_files[0]
        logger.debug(f"Reading output from {latest_file}")

        return latest_file.read_text(encoding="utf-8")

    def _build_ui_prompt(
        self, feature_requirements: str, architect_output: str, openapi_output: str
    ) -> str:
        return f"""You are Agent 03 UI, responsible for UI/UX skeleton generation.

Your role is defined by this specification:

{self.prompt_spec}

---

Agent 00 Meta provided these feature requirements:

{feature_requirements}

---

Agent 01 Architect provided this technical architecture:

{architect_output}

---

Agent 02 OpenAPI provided this API specification:

{openapi_output}

---

Please generate a complete UI skeleton specification following the format specified in your role definition.

Your output MUST include:
1. # UI Skeleton: [Feature Name]
2. ## Component Hierarchy (with tree diagram)
3. ## Routing Structure (routes and protection)
4. ## Layout Structure (responsive breakpoints)
5. ## Component Specifications (for each major component: props, state, events, API integration)
6. ## State Management Strategy
7. ## Data Flow (API to UI)
8. ## Navigation and User Flows

Ensure all user stories from requirements have corresponding UI components and workflows.
Follow responsive design principles (mobile-first), component composition patterns, and accessibility best practices.
Map all API endpoints from the OpenAPI spec to appropriate UI integration points.
"""

    def _validate_output(self, output: str) -> None:
        required_sections = [
            "# UI Skeleton:",
            "## Component Hierarchy",
            "## Routing Structure",
            "## Component Specifications",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in output:
                missing_sections.append(section)

        if missing_sections:
            raise ValueError(
                f"UI skeleton missing required sections: {', '.join(missing_sections)}"
            )

        logger.debug("UI skeleton validation passed")
