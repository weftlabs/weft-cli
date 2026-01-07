"""Data models for code generation and patch application."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PatchAction(str, Enum):
    """Action to take for a code patch."""

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


@dataclass
class CodePatch:
    """Represents a code change to apply to the repository.

    Each patch contains the full content for a file and metadata about
    where and how to apply it.
    """

    file_path: str
    content: str
    language: str
    action: PatchAction = PatchAction.CREATE

    def __post_init__(self) -> None:
        if isinstance(self.action, str):
            self.action = PatchAction(self.action)


@dataclass
class CodeArtifact:
    """Agent output containing code patches and metadata.

    This wraps one or more code patches along with a human-readable
    summary and optional metadata for tracking and audit purposes.
    """

    patches: list[CodePatch]
    summary: str
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def file_count(self) -> int:
        """Number of files affected by this artifact."""
        return len(self.patches)

    @property
    def file_paths(self) -> list[str]:
        """List of all file paths in this artifact."""
        return [patch.file_path for patch in self.patches]


@dataclass
class ApplyResult:
    """Result of applying a single code patch."""

    success: bool
    file_path: str
    error: str | None = None
    warning: str | None = None

    @property
    def has_issues(self) -> bool:
        """Whether this result has errors or warnings."""
        return self.error is not None or self.warning is not None
