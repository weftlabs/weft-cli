"""Agent orchestration utilities."""

import time
from pathlib import Path

import click

from weft.queue.file_ops import get_default_conversation_id, write_prompt
from weft.queue.models import PromptTask


def submit_prompt_to_agent(
    feature_id: str,
    agent_id: str,
    prompt_content: str,
    ai_history_path: Path,
    revision: int | None = None,
    conversation_id: str | None = "auto",
) -> Path:
    """Pass conversation_id="auto" to auto-generate from feature_id+agent_id."""
    # Auto-generate conversation ID if "auto"
    if conversation_id == "auto":
        conversation_id = get_default_conversation_id(feature_id, agent_id)

    prompt_task = PromptTask(
        feature_id=feature_id,
        agent_id=agent_id,
        prompt_text=prompt_content,
        spec_version="1.0.0",
        revision=revision,
        conversation_id=conversation_id,
    )

    prompt_file = write_prompt(
        ai_history_path=ai_history_path,
        feature_id=feature_id,
        agent_id=agent_id,
        prompt_task=prompt_task,
    )

    return prompt_file


def wait_for_agent_result(
    feature_id: str,
    agent_id: str,
    ai_history_path: Path,
    timeout: int = 300,
    min_timestamp: float | None = None,
    show_progress: bool = True,
) -> str | None:
    output_dir = ai_history_path / feature_id / agent_id / "out"
    output_dir.mkdir(parents=True, exist_ok=True)

    start = time.time()
    if min_timestamp is None:
        min_timestamp = start

    if show_progress:
        with click.progressbar(
            length=timeout,
            label=f"⏳ Waiting for Agent {agent_id}",
            show_eta=True,
        ) as bar:
            elapsed = 0
            while elapsed < timeout:
                results = list(output_dir.glob("*_result.md"))
                if results:
                    new_results = [r for r in results if r.stat().st_mtime > min_timestamp]
                    if new_results:
                        latest = max(new_results, key=lambda p: p.stat().st_mtime)
                        bar.update(timeout)
                        return latest.read_text()

                time.sleep(2)
                elapsed = int(time.time() - start)
                bar.update(min(2, timeout - elapsed))
    else:
        elapsed = 0
        while elapsed < timeout:
            results = list(output_dir.glob("*_result.md"))
            if results:
                new_results = [r for r in results if r.stat().st_mtime > min_timestamp]
                if new_results:
                    latest = max(new_results, key=lambda p: p.stat().st_mtime)
                    return latest.read_text()

            time.sleep(2)
            elapsed = int(time.time() - start)

    return None
