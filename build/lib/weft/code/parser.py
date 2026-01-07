"""Parse code blocks from markdown with metadata."""

import logging
import re

from weft.code.models import CodePatch, PatchAction

logger = logging.getLogger(__name__)


def parse_code_from_markdown(markdown: str) -> list[CodePatch]:
    """Extracts code fences with path= and optional action= attributes."""
    patches = []

    # Regex to match code fences with metadata
    # Matches: ```<lang> path=<path> [action=<action>]
    pattern = r"```(\w+)\s+path=([^\s]+)(?:\s+action=(\w+))?\s*\n(.*?)```"

    matches = re.finditer(pattern, markdown, re.DOTALL)

    for match in matches:
        language = match.group(1)
        file_path = match.group(2)
        action_str = match.group(3) or "create"
        content = match.group(4)

        # Validate action
        try:
            action = PatchAction(action_str.lower())
        except ValueError:
            logger.warning(f"Invalid action '{action_str}' for {file_path}, defaulting to 'create'")
            action = PatchAction.CREATE

        # Clean up content (remove trailing newline if present)
        content = content.rstrip("\n")

        patch = CodePatch(
            file_path=file_path,
            content=content,
            language=language,
            action=action,
        )

        patches.append(patch)
        logger.debug(f"Extracted code patch: {file_path} ({language}, {action.value})")

    if not patches:
        logger.debug("No code blocks with metadata found in markdown")
    else:
        logger.info(f"Extracted {len(patches)} code patch(es) from markdown")

    return patches


def has_code_patches(markdown: str) -> bool:
    pattern = r"```\w+\s+path="
    return re.search(pattern, markdown) is not None
