#!/usr/bin/env python3
"""Generic watcher entry point for Docker container execution."""

import logging
import os
import sys
import time
from datetime import UTC
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


def discover_features(ai_history_path: Path) -> list[str]:
    if not ai_history_path.exists():
        return []

    features = []
    for item in ai_history_path.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            # Check if it has agent subdirectories (looks like a feature)
            agent_dirs = [
                d
                for d in item.iterdir()
                if d.is_dir() and d.name.startswith(("00-", "01-", "02-", "03-", "04-", "05-"))
            ]
            if agent_dirs:
                features.append(item.name)

    return sorted(features)


def watch_all_features(agent_id: str, ai_history_path: Path, poll_interval: int = 5) -> None:
    from datetime import datetime

    from weft.agents.base_spec_agent import BaseSpecAgent
    from weft.ai.backend import create_backend_from_config
    from weft.audit.hashing import sha256_hash
    from weft.queue.file_ops import list_pending_prompts, mark_processed, read_prompt, write_result
    from weft.queue.models import ResultTask

    logger.info(f"Starting multi-feature watcher for agent: {agent_id}")
    logger.info(f"Monitoring: {ai_history_path}")
    logger.info(f"Poll interval: {poll_interval}s")

    # Create AI backend
    try:
        backend = create_backend_from_config()
        model_info = backend.get_model_info()
        logger.info(f"Using AI backend: {model_info['backend']} ({model_info['model']})")
    except Exception as e:
        logger.error(f"Failed to create AI backend: {e}")
        sys.exit(1)

    # Cache of watcher instances per feature
    watchers: dict[str, BaseSpecAgent] = {}
    last_features = set()

    while True:
        try:
            # Discover current features
            current_features = discover_features(ai_history_path)
            current_feature_set = set(current_features)

            # Log new features
            new_features = current_feature_set - last_features
            if new_features:
                logger.info(f"Discovered new features: {', '.join(sorted(new_features))}")

            last_features = current_feature_set

            # Process each feature
            for feature_id in current_features:
                agent_dir = ai_history_path / feature_id / agent_id

                if not agent_dir.exists():
                    continue

                # Create watcher instance for this feature if not exists
                if feature_id not in watchers:
                    try:
                        logger.info(f"[{feature_id}] Creating BaseSpecAgent watcher for {agent_id}")
                        watchers[feature_id] = BaseSpecAgent(
                            feature_id=feature_id,
                            agent_id=agent_id,
                            ai_history_path=ai_history_path,
                            backend=backend,
                            poll_interval=poll_interval,
                        )
                    except Exception as e:
                        logger.error(f"[{feature_id}] Failed to create watcher: {e}", exc_info=True)
                        continue

                watcher = watchers[feature_id]

                # Check for pending prompts
                try:
                    pending = list_pending_prompts(agent_dir)
                    if pending:
                        logger.info(f"[{feature_id}] Found {len(pending)} pending prompt(s)")

                        for prompt_file in pending:
                            try:
                                logger.info(f"[{feature_id}] Processing: {prompt_file.name}")

                                # Read prompt
                                prompt_task = read_prompt(prompt_file)
                                prompt_hash = sha256_hash(prompt_task.prompt_text)

                                # Process using BaseSpecAgent (handles spec loading, code extraction, etc.)
                                start_time = time.time()
                                output_text = watcher.process_prompt(prompt_task)
                                duration = time.time() - start_time

                                output_hash = sha256_hash(output_text)

                                logger.info(
                                    f"[{feature_id}] Generated output in {duration:.2f}s "
                                    f"(prompt: {prompt_hash[:8]}, output: {output_hash[:8]})"
                                )

                                # Post-process to extract and apply code patches
                                code_artifact = watcher.post_process_result(
                                    output_text, prompt_task
                                )

                                # Create result
                                result = ResultTask(
                                    feature_id=feature_id,
                                    agent_id=agent_id,
                                    output_text=output_text,
                                    prompt_hash=prompt_hash,
                                    output_hash=output_hash,
                                    timestamp=datetime.now(UTC),
                                    conversation_id=prompt_task.conversation_id,
                                    code_artifact=code_artifact,
                                )

                                # Write result
                                result_path = write_result(
                                    ai_history_path,
                                    feature_id,
                                    agent_id,
                                    result,
                                )

                                logger.info(f"[{feature_id}] Wrote result: {result_path.name}")

                                # Mark as processed
                                mark_processed(prompt_file)
                                logger.info(f"[{feature_id}] Marked processed: {prompt_file.name}")

                            except Exception as e:
                                logger.error(
                                    f"[{feature_id}] Failed to process {prompt_file.name}: {e}",
                                    exc_info=True,
                                )

                except Exception as e:
                    logger.error(f"[{feature_id}] Error listing prompts: {e}")

        except Exception as e:
            logger.error(f"Error in watch loop: {e}", exc_info=True)

        time.sleep(poll_interval)


def main() -> None:
    # Get required environment variables
    agent_id = os.getenv("AGENT_ID")
    if not agent_id:
        logger.error("AGENT_ID environment variable is required")
        sys.exit(1)

    # Try WEFT_AI_HISTORY_PATH first (set by runtime), fall back to AI_HISTORY_PATH
    ai_history_path = os.getenv("WEFT_AI_HISTORY_PATH") or os.getenv("AI_HISTORY_PATH")
    if not ai_history_path:
        logger.error("WEFT_AI_HISTORY_PATH or AI_HISTORY_PATH environment variable is required")
        sys.exit(1)

    ai_history_path = Path(ai_history_path)

    poll_interval = int(os.getenv("WEFT_POLL_INTERVAL") or os.getenv("POLL_INTERVAL", "5"))

    # Normalize agent ID
    agent_map = {
        "meta": "00-meta",
        "architect": "01-architect",
        "openapi": "02-openapi",
        "ui": "03-ui",
        "integration": "04-integration",
        "test": "05-test",
    }

    agent_id = agent_map.get(agent_id, agent_id)

    # Validate agent ID format
    valid_agents = ["00-meta", "01-architect", "02-openapi", "03-ui", "04-integration", "05-test"]
    if agent_id not in valid_agents:
        logger.error(f"Unknown agent ID: {agent_id}")
        logger.error(f"Valid agent IDs: {', '.join(valid_agents)}")
        sys.exit(1)

    # Start watching all features
    try:
        watch_all_features(agent_id, ai_history_path, poll_interval)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping...")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
