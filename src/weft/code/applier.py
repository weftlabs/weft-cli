"""Apply code patches to Git worktrees."""

import builtins
import contextlib
import logging
import os
import subprocess
import tempfile
from pathlib import Path

from weft.code.models import ApplyResult, CodeArtifact, CodePatch, PatchAction

logger = logging.getLogger(__name__)


class PatchApplier:
    def __init__(self, worktree_path: Path):
        self.worktree_path = worktree_path.resolve()

        if not self.worktree_path.exists():
            raise ValueError(f"Worktree path does not exist: {self.worktree_path}")

    def apply_patch(self, patch: CodePatch) -> ApplyResult:
        target_file = self.worktree_path / patch.file_path

        logger.debug(f"Applying patch: {patch.file_path} (action={patch.action.value})")

        try:
            if patch.action == PatchAction.DELETE:
                return self._delete_file(target_file, patch.file_path)
            elif patch.action in (PatchAction.CREATE, PatchAction.UPDATE):
                return self._write_file(target_file, patch)
            else:
                return ApplyResult(
                    success=False,
                    file_path=patch.file_path,
                    error=f"Unknown action: {patch.action}",
                )

        except Exception as e:
            logger.exception(f"Failed to apply patch to {patch.file_path}")
            return ApplyResult(success=False, file_path=patch.file_path, error=str(e))

    def _write_file(self, target_file: Path, patch: CodePatch) -> ApplyResult:
        # Create parent directories if needed
        target_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if file exists for action validation
        file_exists = target_file.exists()

        warning = None
        if patch.action == PatchAction.CREATE and file_exists:
            warning = f"File already exists, overwriting: {patch.file_path}"
            logger.warning(warning)
        elif patch.action == PatchAction.UPDATE and not file_exists:
            warning = f"File does not exist, creating: {patch.file_path}"
            logger.warning(warning)

        # Write atomically: create temp file in same directory, then rename
        # This ensures we never have partial/corrupted files
        temp_fd = None
        temp_path = None

        try:
            # Create temp file in same directory as target
            temp_fd, temp_path = tempfile.mkstemp(
                dir=target_file.parent, prefix=".weft_tmp_", text=True
            )

            # Write content to temp file
            with os.fdopen(temp_fd, "w", encoding="utf-8") as f:
                f.write(patch.content)
                temp_fd = None  # File descriptor is closed by fdopen context

            # Atomic rename
            os.replace(temp_path, target_file)
            temp_path = None  # Renamed successfully

            logger.debug(f"Wrote {len(patch.content)} bytes to {patch.file_path}")

        finally:
            # Clean up temp file if it still exists (error case)
            if temp_fd is not None:
                with contextlib.suppress(builtins.BaseException):
                    os.close(temp_fd)
            if temp_path and os.path.exists(temp_path):
                with contextlib.suppress(builtins.BaseException):
                    os.unlink(temp_path)

        # Stage file in git
        try:
            subprocess.run(
                ["git", "add", str(target_file)],
                cwd=self.worktree_path,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.debug(f"Staged {patch.file_path} in git")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to stage {patch.file_path}: {e.stderr}")
            return ApplyResult(
                success=False,
                file_path=patch.file_path,
                error=f"Git add failed: {e.stderr}",
                warning=warning,
            )

        return ApplyResult(success=True, file_path=patch.file_path, warning=warning)

    def _delete_file(self, target_file: Path, file_path: str) -> ApplyResult:
        if not target_file.exists():
            warning = f"File does not exist, nothing to delete: {file_path}"
            logger.warning(warning)
            return ApplyResult(success=True, file_path=file_path, warning=warning)

        try:
            # Remove from git and filesystem
            subprocess.run(
                ["git", "rm", str(target_file)],
                cwd=self.worktree_path,
                check=True,
                capture_output=True,
                text=True,
            )
            logger.debug(f"Deleted and staged removal: {file_path}")
            return ApplyResult(success=True, file_path=file_path)

        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to delete {file_path}: {e.stderr}")
            return ApplyResult(
                success=False, file_path=file_path, error=f"Git rm failed: {e.stderr}"
            )

    def apply_artifact(self, artifact: CodeArtifact) -> list[ApplyResult]:
        """Attempts all patches even if some fail."""
        if not artifact.patches:
            logger.warning("Code artifact contains no patches")
            return []

        logger.info(
            f"Applying code artifact with {len(artifact.patches)} patch(es): " f"{artifact.summary}"
        )

        results = []
        success_count = 0
        failure_count = 0

        for patch in artifact.patches:
            result = self.apply_patch(patch)
            results.append(result)

            if result.success:
                success_count += 1
            else:
                failure_count += 1
                logger.warning(f"Patch failed for {patch.file_path}: {result.error}")

        logger.info(f"Applied artifact: {success_count} succeeded, {failure_count} failed")

        return results
