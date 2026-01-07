"""Git worktree operations for parallel feature development."""

import logging
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WorktreeInfo:
    path: Path
    branch: str
    feature_id: str
    created_at: datetime


@dataclass
class WorktreeStatus:
    is_clean: bool
    modified_files: list[str]
    untracked_files: list[str]
    current_branch: str


def create_worktree(repo_path: Path, feature_id: str, base_branch: str = "main") -> Path:
    repo_path = repo_path.resolve()

    # Validate repository
    if not (repo_path / ".git").exists():
        raise ValueError(f"Not a git repository: {repo_path}")

    logger.debug(f"Creating worktree for {feature_id} in {repo_path}")

    # Create worktrees directory if needed
    worktrees_dir = repo_path / "worktrees"
    worktrees_dir.mkdir(exist_ok=True)

    # Target worktree path
    worktree_path = worktrees_dir / feature_id

    # Check if worktree already exists
    if worktree_path.exists():
        raise ValueError(f"Worktree already exists: {worktree_path}")

    # Branch name
    branch_name = f"feature/{feature_id}"

    logger.info(f"Creating worktree at {worktree_path} with branch {branch_name}")

    # Create worktree and branch
    try:
        # git worktree add -b feature/feat-123 worktrees/feat-123 main
        subprocess.run(
            [
                "git",
                "worktree",
                "add",
                "-b",
                branch_name,
                str(worktree_path),
                base_branch,
            ],
            cwd=repo_path,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as e:
        # Clean up if creation failed
        if worktree_path.exists():
            shutil.rmtree(worktree_path)

        stderr = e.stderr.strip()
        # Log at debug level to avoid cluttering user output with raw git errors
        logger.debug(f"Git worktree command failed: {stderr}")

        # Parse common git errors and provide helpful messages
        if "already exists" in stderr:
            raise ValueError(
                f"Branch '{branch_name}' already exists.\n"
                f"This feature may have been created previously.\n"
                f"To resume: Check existing features with 'weft feature list'\n"
                f"To remove: Run 'weft feature drop {feature_id}'"
            ) from e
        elif (
            "not a valid" in stderr or "unknown revision" in stderr or "invalid reference" in stderr
        ):
            raise ValueError(
                f"Base branch '{base_branch}' not found.\n"
                f"Make sure the base branch exists in your repository."
            ) from e
        else:
            # Generic error with cleaned up message
            raise ValueError(f"Failed to create worktree: {stderr}") from e

    logger.info(f"Successfully created worktree at {worktree_path}")
    return worktree_path


def list_worktrees(repo_path: Path) -> list[WorktreeInfo]:
    repo_path = repo_path.resolve()

    # Validate repository
    if not (repo_path / ".git").exists():
        raise ValueError(f"Not a git repository: {repo_path}")

    logger.debug(f"Listing worktrees in {repo_path}")

    # git worktree list --porcelain
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=repo_path,
        check=True,
        capture_output=True,
        text=True,
    )

    worktrees = []
    current_worktree: dict[str, Path | str | datetime] = {}

    for line in result.stdout.strip().split("\n"):
        if line.startswith("worktree "):
            path = Path(line.split(" ", 1)[1])
            current_worktree["path"] = path
        elif line.startswith("branch "):
            branch = line.split(" ", 1)[1].replace("refs/heads/", "")
            current_worktree["branch"] = branch

            # Extract feature_id from branch (feature/feat-123 -> feat-123)
            if branch.startswith("feature/"):
                feature_id = branch.replace("feature/", "")
                current_worktree["feature_id"] = feature_id

                # Get creation time from directory
                worktree_path = current_worktree["path"]
                assert isinstance(worktree_path, Path)
                if worktree_path.exists():
                    stat = worktree_path.stat()
                    created_at = datetime.fromtimestamp(stat.st_ctime)
                else:
                    # If path doesn't exist, use current time as fallback
                    created_at = datetime.now()

                current_worktree["created_at"] = created_at

                worktrees.append(
                    WorktreeInfo(
                        path=current_worktree["path"],  # type: ignore[arg-type]
                        branch=current_worktree["branch"],  # type: ignore[arg-type]
                        feature_id=current_worktree["feature_id"],  # type: ignore[arg-type]
                        created_at=current_worktree["created_at"],  # type: ignore[arg-type]
                    )
                )
                current_worktree = {}

    logger.debug(f"Found {len(worktrees)} feature worktrees")
    return worktrees


def remove_worktree(repo_path: Path, feature_id: str, delete_branch: bool = False) -> bool:
    repo_path = repo_path.resolve()
    worktree_path = repo_path / "worktrees" / feature_id

    logger.debug(f"Removing worktree for {feature_id}")

    worktree_removed = False
    branch_deleted = False

    # Try to remove worktree if it exists
    if worktree_path.exists():
        try:
            # Remove worktree (use --force to handle modified files)
            # git worktree remove --force worktrees/feat-123
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(worktree_path)],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Removed worktree at {worktree_path}")
            worktree_removed = True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error removing worktree: {e.stderr}")
    else:
        logger.debug(f"Worktree does not exist: {worktree_path}")

    # Delete branch if requested (independent of worktree removal)
    if delete_branch:
        branch_name = f"feature/{feature_id}"
        try:
            subprocess.run(
                ["git", "branch", "-D", branch_name],
                cwd=repo_path,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.info(f"Deleted branch {branch_name}")
            branch_deleted = True
        except subprocess.CalledProcessError as e:
            logger.debug(f"Error deleting branch {branch_name}: {e.stderr}")

    # Return True if either operation succeeded
    return worktree_removed or branch_deleted


def get_worktree_status(worktree_path: Path) -> WorktreeStatus:
    worktree_path = worktree_path.resolve()

    logger.debug(f"Getting status for worktree at {worktree_path}")

    # Get current branch
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
        text=True,
    )
    current_branch = result.stdout.strip()

    # Get status
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=worktree_path,
        check=True,
        capture_output=True,
        text=True,
    )

    modified_files = []
    untracked_files = []

    for line in result.stdout.strip().split("\n"):
        if not line:
            continue

        # Git status --porcelain format: XY filename
        # where X=staged status, Y=unstaged status
        # After the 2-char status code, there's one or more spaces before filename
        status_code = line[:2]
        filename = line[2:].lstrip()  # Skip status code and any whitespace

        if status_code.strip() == "??":
            untracked_files.append(filename)
        else:
            modified_files.append(filename)

    is_clean = len(modified_files) == 0 and len(untracked_files) == 0

    logger.debug(
        f"Worktree status: clean={is_clean}, "
        f"modified={len(modified_files)}, untracked={len(untracked_files)}"
    )

    return WorktreeStatus(
        is_clean=is_clean,
        modified_files=modified_files,
        untracked_files=untracked_files,
        current_branch=current_branch,
    )


def get_worktree_path(code_repo_path: Path, feature_name: str) -> Path:
    return code_repo_path / "worktrees" / feature_name
