"""Agent 04 Integration - API integration layer and state management.

The Integration agent receives architecture, API specs, and UI design, then generates
integration layer code including API clients, data fetching, state management, and
form integration with error handling.
"""

import logging
import re
from pathlib import Path
from typing import Optional

from weft.ai.backend import AIBackend
from weft.queue.models import PromptTask
from weft.watchers.base import BaseWatcher

logger = logging.getLogger(__name__)


class IntegrationWatcher(BaseWatcher):
    """Agent 04 Integration - API integration layer generation.

    Receives architecture from Agent 01, API specs from Agent 02, and UI design from
    Agent 03, then generates complete integration layer including API clients,
    React Query hooks, state management, form integration, and error handling.

    The Integration agent follows type-safe patterns, implements caching strategies,
    and ensures proper error handling and loading states.
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
            prompt_spec_path = Path("prompt-specs/v1.0.0/04-integration.md")

        self.prompt_spec = self._load_prompt_spec(prompt_spec_path)
        self.spec_version = self._extract_spec_version(self.prompt_spec)

        logger.info(
            f"IntegrationWatcher initialized with spec version {self.spec_version} "
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
            f"Processing integration layer generation request: {feature_requirements[:100]}..."
            if len(feature_requirements) > 100
            else f"Processing integration layer generation request: {feature_requirements}"
        )

        architect_output = self._read_previous_agent_output("01-architect")
        openapi_output = self._read_previous_agent_output("02-openapi")
        ui_output = self._read_previous_agent_output("03-ui")

        logger.debug(f"Architect output length: {len(architect_output)} characters")
        logger.debug(f"OpenAPI output length: {len(openapi_output)} characters")
        logger.debug(f"UI output length: {len(ui_output)} characters")

        integration_prompt = self._build_integration_prompt(
            feature_requirements, architect_output, openapi_output, ui_output
        )

        logger.debug(f"Integration prompt length: {len(integration_prompt)} characters")

        output = self.backend.generate(integration_prompt)

        logger.info(f"Generated integration layer: {len(output)} characters")

        self._validate_output(output)

        logger.info("Integration layer validated successfully")

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

    def _build_integration_prompt(
        self,
        feature_requirements: str,
        architect_output: str,
        openapi_output: str,
        ui_output: str,
    ) -> str:
        return f"""You are Agent 04 Integration, responsible for API integration layer generation.

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

Agent 03 UI provided this UI skeleton:

{ui_output}

---

Please generate a complete integration layer specification following the format specified in your role definition.

Your output MUST include:
1. # Integration Layer: [Feature Name]
2. ## API Client Configuration (Axios setup, interceptors)
3. ## API Service Layer (typed service methods for all endpoints)
4. ## Data Fetching Strategy (React Query setup, cache invalidation)
5. ## React Hooks / Custom Hooks (queries, mutations, error handling)
6. ## Type Definitions (TypeScript interfaces for all models)
7. ## Error Handling (parsing, user-friendly messages)
8. ## Component Integration Examples (connecting UI to APIs)

Ensure all OpenAPI endpoints have corresponding service methods.
Map all UI components' API integration points to appropriate hooks.
Follow type-safe patterns with TypeScript throughout.
Implement proper caching, error handling, and loading states.
"""

    def _validate_output(self, output: str) -> None:
        required_sections = [
            "# Integration Layer:",
            "## API Client Configuration",
            "## API Service Layer",
            "## Data Fetching Strategy",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in output:
                missing_sections.append(section)

        if missing_sections:
            raise ValueError(
                f"Integration layer missing required sections: {', '.join(missing_sections)}"
            )

        logger.debug("Integration layer validation passed")
