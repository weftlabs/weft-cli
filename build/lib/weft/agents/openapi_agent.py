"""Agent 02 OpenAPI - API specification generation from domain models.

The OpenAPI agent receives architecture from Agent 01 Architect and generates
complete OpenAPI 3.0 specifications with endpoints, schemas, security, and examples.
"""

import logging
import re
from pathlib import Path
from typing import Optional

from weft.ai.backend import AIBackend
from weft.queue.models import PromptTask
from weft.watchers.base import BaseWatcher

logger = logging.getLogger(__name__)


class OpenAPIWatcher(BaseWatcher):
    """Agent 02 OpenAPI - API specification generation.

    Receives architecture from Agent 01 Architect and generates complete OpenAPI 3.0
    specifications including endpoints, request/response schemas, security definitions,
    and comprehensive examples.

    The OpenAPI agent follows RESTful principles, includes validation constraints,
    and ensures API security best practices.
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
            prompt_spec_path = Path("prompt-specs/v1.0.0/02-openapi.md")

        self.prompt_spec = self._load_prompt_spec(prompt_spec_path)
        self.spec_version = self._extract_spec_version(self.prompt_spec)

        logger.info(
            f"OpenAPIWatcher initialized with spec version {self.spec_version} "
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
            f"Processing OpenAPI generation request: {feature_requirements[:100]}..."
            if len(feature_requirements) > 100
            else f"Processing OpenAPI generation request: {feature_requirements}"
        )

        architect_output = self._read_previous_agent_output("01-architect")

        logger.debug(f"Architect output length: {len(architect_output)} characters")

        openapi_prompt = self._build_openapi_prompt(
            feature_requirements, architect_output
        )

        logger.debug(f"OpenAPI prompt length: {len(openapi_prompt)} characters")

        output = self.backend.generate(openapi_prompt)

        logger.info(f"Generated OpenAPI spec: {len(output)} characters")

        self._validate_output(output)

        logger.info("OpenAPI specification validated successfully")

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

    def _build_openapi_prompt(
        self, feature_requirements: str, architect_output: str
    ) -> str:
        return f"""You are Agent 02 OpenAPI, responsible for API specification generation.

Your role is defined by this specification:

{self.prompt_spec}

---

Agent 00 Meta provided these feature requirements:

{feature_requirements}

---

Agent 01 Architect provided this technical architecture:

{architect_output}

---

Please generate a complete OpenAPI 3.0 specification following the format specified in your role definition.

Your output MUST include:
1. openapi: 3.0.0 (version declaration)
2. info: (title, version, description)
3. servers: (server URLs for different environments)
4. paths: (all API endpoints with full specifications)
5. components: (schemas, securitySchemes, responses)
6. security: (global security requirements)
7. tags: (endpoint grouping)

Ensure all endpoints from the Architect's API Requirements section are fully specified with:
- Request parameters (path, query, header)
- Request body schemas (for POST/PUT/PATCH)
- Response schemas (success and error cases)
- Security requirements
- Examples

Follow RESTful conventions and OpenAPI 3.0 standards strictly.
"""

    def _validate_output(self, output: str) -> None:
        required_sections = [
            "openapi:",
            "info:",
            "paths:",
            "components:",
        ]

        missing_sections = []
        for section in required_sections:
            if section not in output:
                missing_sections.append(section)

        if missing_sections:
            raise ValueError(
                f"OpenAPI specification missing required sections: {', '.join(missing_sections)}"
            )

        if "title:" not in output or "version:" not in output:
            raise ValueError("OpenAPI specification missing info.title or info.version")

        logger.debug("OpenAPI specification validation passed")
