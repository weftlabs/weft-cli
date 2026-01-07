"""AI history repository management and structure creation."""

import subprocess
from pathlib import Path


def initialize_ai_history_repo(path: Path) -> bool:
    """Initialize an AI history repository.

    Creates the directory if it doesn't exist and initializes a Git repository.
    """
    try:
        # Create directory if it doesn't exist
        path.mkdir(parents=True, exist_ok=True)

        # Initialize git repository
        result = subprocess.run(
            ["git", "init"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )

        return result.returncode == 0

    except (OSError, subprocess.SubprocessError):
        return False


def validate_ai_history_repo(path: Path) -> bool:
    """Validate that a path is a valid AI history repository.

    Checks if the path exists and contains a Git repository.
    """
    # Check if path exists
    if not path.exists():
        return False

    # Check if path is a directory
    if not path.is_dir():
        return False

    # Check if .git directory exists
    git_dir = path / ".git"
    if not git_dir.exists():
        return False

    # Verify it's a valid git repository
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def create_feature_structure(ai_history_path: Path, feature_id: str, agents: list[str]) -> None:
    """Create directory structure for a feature in AI history.

    Creates the feature directory and subdirectories for each agent
    with in/, out/, and log/ folders.
    """
    # Validate the AI history repository
    if not validate_ai_history_repo(ai_history_path):
        raise ValueError(
            f"Invalid AI history repository: {ai_history_path}\n"
            f"The directory must be a git repository.\n"
            f"Fix: Run 'weft project-init' to initialize, or manually run:\n"
            f"  cd {ai_history_path} && git init"
        )

    # Create feature directory
    feature_path = ai_history_path / feature_id
    feature_path.mkdir(parents=True, exist_ok=True)

    # Create agent directories with in/, out/, log/ subdirectories
    for agent_id in agents:
        agent_path = feature_path / agent_id
        (agent_path / "in").mkdir(parents=True, exist_ok=True)
        (agent_path / "out").mkdir(parents=True, exist_ok=True)
        (agent_path / "log").mkdir(parents=True, exist_ok=True)


def get_feature_agents(ai_history_path: Path, feature_id: str) -> list[str]:
    """Get list of agent IDs for a feature.

    Scans the feature directory and returns all agent subdirectories.
    """
    # Validate the AI history repository
    if not validate_ai_history_repo(ai_history_path):
        raise ValueError(
            f"Invalid AI history repository: {ai_history_path}\n"
            f"The directory must be a git repository.\n"
            f"Fix: Run 'weft init' to initialize, or manually run:\n"
            f"  cd {ai_history_path} && git init"
        )

    # Check if feature directory exists
    feature_path = ai_history_path / feature_id
    if not feature_path.exists():
        raise FileNotFoundError(f"Feature directory not found: {feature_path}")

    # Get all subdirectories that are agent directories
    # An agent directory should have in/, out/, and log/ subdirectories
    agents = []
    for item in feature_path.iterdir():
        if item.is_dir():
            # Check if it has the expected agent structure
            has_in = (item / "in").exists()
            has_out = (item / "out").exists()
            has_log = (item / "log").exists()

            if has_in and has_out and has_log:
                agents.append(item.name)

    return sorted(agents)
