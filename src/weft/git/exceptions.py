"""Git-related exceptions."""


class GitError(Exception):
    """Base exception for git operations."""

    pass


class MergeConflictError(GitError):
    """Raised when a git merge results in conflicts."""

    pass


class WorktreeError(GitError):
    """Raised when worktree operations fail."""

    pass


class BranchError(GitError):
    """Raised when branch operations fail."""

    pass
