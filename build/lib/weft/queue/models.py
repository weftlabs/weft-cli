"""Data models for task queue system.

Defines structures for prompts, results, and task status that are
serialized to/from markdown files with YAML frontmatter.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional

import yaml

from weft.audit.hashing import create_audit_frontmatter

if TYPE_CHECKING:
    from weft.code.models import CodeArtifact


class TaskStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


@dataclass
class PromptTask:
    feature_id: str
    agent_id: str
    prompt_text: str
    spec_version: str = "1.0.0"
    revision: int | None = None
    conversation_id: str | None = None


@dataclass
class ResultTask:
    feature_id: str
    agent_id: str
    output_text: str
    prompt_hash: str
    output_hash: str
    timestamp: datetime
    code_artifact: Optional["CodeArtifact"] = None
    conversation_id: str | None = None


def prompt_to_markdown(prompt: PromptTask) -> str:
    frontmatter = {
        "feature": prompt.feature_id,
        "agent": prompt.agent_id,
        "prompt_spec_version": prompt.spec_version,
    }

    if prompt.revision is not None:
        frontmatter["revision"] = prompt.revision

    if prompt.conversation_id is not None:
        frontmatter["conversation_id"] = prompt.conversation_id

    yaml_str = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_str}---\n\n{prompt.prompt_text}"


def markdown_to_prompt(content: str) -> PromptTask:
    # Split frontmatter and content
    parts = content.split("---", 2)
    if len(parts) < 3:
        raise ValueError("Invalid markdown format: missing frontmatter delimiters")

    # Parse YAML frontmatter
    try:
        frontmatter = yaml.safe_load(parts[1])
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML frontmatter: {e}") from e

    if not isinstance(frontmatter, dict):
        raise ValueError("Frontmatter must be a YAML dictionary")

    # Extract required fields
    if "feature" not in frontmatter:
        raise ValueError("Missing required field 'feature' in frontmatter")
    if "agent" not in frontmatter:
        raise ValueError("Missing required field 'agent' in frontmatter")

    # Extract prompt text (everything after second ---)
    prompt_text = parts[2].strip()

    return PromptTask(
        feature_id=frontmatter["feature"],
        agent_id=frontmatter["agent"],
        prompt_text=prompt_text,
        spec_version=frontmatter.get("prompt_spec_version", "1.0.0"),
        revision=frontmatter.get("revision", 1),
        conversation_id=frontmatter.get("conversation_id", None),
    )


def result_to_markdown(result: ResultTask) -> str:
    # Create audit frontmatter
    frontmatter = create_audit_frontmatter(
        feature=result.feature_id,
        agent=result.agent_id,
        prompt_hash=result.prompt_hash,
        output_hash=result.output_hash,
        spec_version="1.0.0",  # Could be extracted from result if needed
        conversation_id=result.conversation_id,
    )

    # Combine frontmatter with output
    return f"{frontmatter}\n{result.output_text}"
