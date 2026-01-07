"""File-based task queue operations."""

import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from weft.queue.models import (
    PromptTask,
    ResultTask,
    markdown_to_prompt,
    prompt_to_markdown,
    result_to_markdown,
)


def get_default_conversation_id(feature_id: str, agent_id: str) -> str:
    """Ensures prompts for same feature/agent share conversation context."""
    # Remove any slashes from feature_id for cleaner conversation ID
    clean_feature = feature_id.replace("/", "-")
    return f"{clean_feature}-{agent_id}"


def write_prompt(
    ai_history_path: Path,
    feature_id: str,
    agent_id: str,
    prompt_task: PromptTask,
) -> Path:
    # Create agent's in/ directory
    agent_path = ai_history_path / feature_id / agent_id / "in"
    agent_path.mkdir(parents=True, exist_ok=True)

    # Generate filename based on revision or timestamp
    if hasattr(prompt_task, "revision") and prompt_task.revision:
        # Sanitize feature_id for use in filename (remove slashes)
        clean_feature = feature_id.replace("/", "-")
        filename = f"{clean_feature}_prompt_v{prompt_task.revision}.md"
    else:
        # Generate filename with UTC timestamp (including microseconds for uniqueness)
        now = datetime.now(UTC)
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        microseconds = f"{now.microsecond:06d}"
        filename = f"{timestamp}_{microseconds}_prompt.md"

    target_path = agent_path / filename

    # Serialize prompt to markdown
    content = prompt_to_markdown(prompt_task)

    # Atomic write: write to temp file, then move
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=agent_path,
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # Atomic move (rename is atomic on POSIX systems)
    shutil.move(str(tmp_path), str(target_path))

    return target_path


def read_prompt(prompt_file: Path) -> PromptTask:
    if not prompt_file.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

    content = prompt_file.read_text(encoding="utf-8")
    return markdown_to_prompt(content)


def write_result(
    ai_history_path: Path,
    feature_id: str,
    agent_id: str,
    result_task: ResultTask,
) -> Path:
    # Create agent's out/ directory
    agent_path = ai_history_path / feature_id / agent_id / "out"
    agent_path.mkdir(parents=True, exist_ok=True)

    # Generate filename with UTC timestamp (including microseconds for uniqueness)
    now = datetime.now(UTC)
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    microseconds = f"{now.microsecond:06d}"
    filename = f"{timestamp}_{microseconds}_result.md"
    target_path = agent_path / filename

    # Serialize result to markdown with audit frontmatter
    content = result_to_markdown(result_task)

    # Atomic write: write to temp file, then move
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=agent_path,
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    # Atomic move
    shutil.move(str(tmp_path), str(target_path))

    return target_path


def mark_processed(prompt_file: Path) -> Path:
    if not prompt_file.exists():
        raise FileNotFoundError(f"File not found: {prompt_file}")

    # Rename .md to .processed
    processed_path = prompt_file.with_suffix(".processed")
    prompt_file.rename(processed_path)

    return processed_path


def list_pending_prompts(agent_dir: Path) -> list[Path]:
    """Sorted by creation time to ensure FIFO processing."""
    in_dir = agent_dir / "in"

    # Return empty list if in/ directory doesn't exist
    if not in_dir.exists():
        return []

    # Get all .md files (excludes .processed)
    prompts = list(in_dir.glob("*.md"))

    # Sort by creation time (oldest first) for FIFO processing
    prompts.sort(key=lambda p: p.stat().st_ctime)

    return prompts
