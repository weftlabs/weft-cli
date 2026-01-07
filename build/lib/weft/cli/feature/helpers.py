"""Feature initialization helpers."""

import logging
import re
from pathlib import Path

from weft.git.worktree import create_worktree, remove_worktree
from weft.history.repo_manager import create_feature_structure

logger = logging.getLogger(__name__)


def validate_feature_id(feature_id: str) -> bool:
    """Validate feature ID format.

    Feature IDs must:
    - Start with a letter
    - Contain only alphanumeric, hyphens, underscores
    - Be 3-50 characters long
    """
    if not feature_id:
        raise ValueError("Feature ID cannot be empty")

    if len(feature_id) < 3 or len(feature_id) > 50:
        raise ValueError("Feature ID must be 3-50 characters")

    if not feature_id[0].isalpha():
        raise ValueError("Feature ID must start with a letter")

    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", feature_id):
        raise ValueError(
            "Feature ID can only contain alphanumeric characters, hyphens, and underscores"
        )

    return True


def initialize_feature(
    feature_id: str,
    code_repo_path: Path,
    ai_history_path: Path,
    base_branch: str = "main",
    agents: list[str] | None = None,
) -> dict:
    """Initialize a new feature for development.

    Creates git worktree and AI history structure.
    """
    # Validate feature ID
    validate_feature_id(feature_id)

    # Default agents
    if agents is None:
        agents = [
            "00-meta",
            "01-architect",
            "02-openapi",
            "03-ui",
            "04-integration",
            "05-test",
        ]

    logger.info(f"Initializing feature {feature_id} with {len(agents)} agents: {', '.join(agents)}")

    # Create worktree
    try:
        worktree_path = create_worktree(code_repo_path, feature_id, base_branch)
        logger.info(f"Created worktree at {worktree_path}")
    except ValueError as e:
        # ValueError already has user-friendly message, just log at debug
        logger.debug(f"Worktree creation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to create worktree: {e}")
        raise ValueError(f"Failed to create worktree: {e}") from e

    # Create AI history structure
    try:
        create_feature_structure(ai_history_path, feature_id, agents)
        logger.info(f"Created AI history structure for {feature_id}")
    except ValueError as e:
        # Rollback worktree if history creation fails
        logger.debug(f"AI history creation failed: {e}, rolling back worktree")
        remove_worktree(code_repo_path, feature_id)
        raise  # Re-raise with original message
    except Exception as e:
        # Rollback worktree if history creation fails
        logger.error(f"Failed to create AI history structure: {e}, rolling back worktree")
        remove_worktree(code_repo_path, feature_id)
        raise ValueError(f"Failed to create AI history structure: {e}") from e

    result = {
        "feature_id": feature_id,
        "worktree_path": worktree_path,
        "history_path": ai_history_path / feature_id,
        "agents": agents,
        "base_branch": base_branch,
        "status": "initialized",
    }

    logger.info(f"Feature {feature_id} initialized successfully")
    return result
