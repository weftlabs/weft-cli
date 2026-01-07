"""Tests for weft.code.applier module."""

import os
import subprocess
from unittest.mock import patch

import pytest

from weft.code.applier import PatchApplier
from weft.code.models import ApplyResult, CodeArtifact, CodePatch, PatchAction


class TestPatchApplierInit:
    """Tests for PatchApplier initialization."""

    def test_init_valid_worktree(self, git_worktree):
        """Test initialization with valid worktree path."""
        applier = PatchApplier(git_worktree)

        assert applier.worktree_path == git_worktree.resolve()
        assert applier.worktree_path.exists()

    def test_init_resolves_path(self, git_worktree):
        """Test that path is resolved to absolute path."""
        applier = PatchApplier(git_worktree)

        assert applier.worktree_path.is_absolute()
        assert applier.worktree_path == git_worktree.resolve()

    def test_init_nonexistent_path_raises(self, tmp_path):
        """Test that nonexistent path raises ValueError."""
        nonexistent = tmp_path / "does_not_exist"

        with pytest.raises(ValueError, match="does not exist"):
            PatchApplier(nonexistent)

    def test_init_stores_resolved_path(self, git_worktree):
        """Test that stored path is resolved (absolute)."""
        applier = PatchApplier(git_worktree)

        assert applier.worktree_path.is_absolute()
        assert applier.worktree_path == git_worktree.resolve()


class TestApplyPatchCreate:
    """Tests for CREATE patch action."""

    def test_create_new_file(self, git_worktree):
        """Test creating a new file."""
        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/new.py",
            content='print("Hello, World!")',
            language="python",
            action=PatchAction.CREATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert result.file_path == "src/new.py"
        assert result.error is None
        assert (git_worktree / "src/new.py").exists()
        assert (git_worktree / "src/new.py").read_text() == 'print("Hello, World!")'

    def test_create_with_parent_dirs(self, git_worktree):
        """Test creating file with nested parent directories."""
        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/utils/helpers/formatter.py",
            content="# Helper",
            language="python",
            action=PatchAction.CREATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert (git_worktree / "src/utils/helpers").exists()
        assert (git_worktree / "src/utils/helpers/formatter.py").exists()

    def test_create_stages_in_git(self, git_worktree):
        """Test that created file is staged in git."""
        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/test.py",
            content="# Test",
            language="python",
            action=PatchAction.CREATE,
        )

        result = applier.apply_patch(patch)

        assert result.success

        # Check git status
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_worktree,
            capture_output=True,
            text=True,
            check=True,
        )
        # File should be staged (starts with A)
        assert "A  src/test.py" in status.stdout or "A src/test.py" in status.stdout

    def test_create_overwrites_existing_with_warning(self, git_worktree):
        """Test that CREATE on existing file overwrites with warning."""
        # Create file first
        existing_file = git_worktree / "src/existing.py"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_text("# Original")

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/existing.py",
            content="# Overwritten",
            language="python",
            action=PatchAction.CREATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert result.warning is not None
        assert "already exists" in result.warning
        assert existing_file.read_text() == "# Overwritten"

    def test_create_empty_content(self, git_worktree):
        """Test creating file with empty content."""
        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/empty.py",
            content="",
            language="python",
            action=PatchAction.CREATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert (git_worktree / "src/empty.py").exists()
        assert (git_worktree / "src/empty.py").read_text() == ""

    def test_create_with_unicode_content(self, git_worktree):
        """Test creating file with unicode content."""
        applier = PatchApplier(git_worktree)
        content = "# 你好世界 🌍\nprint('Hello 世界')"
        patch = CodePatch(
            file_path="src/unicode.py",
            content=content,
            language="python",
            action=PatchAction.CREATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert (git_worktree / "src/unicode.py").read_text() == content

    @patch("subprocess.run")
    def test_create_git_staging_fails(self, mock_run, git_worktree):
        """Test that git staging failure is handled."""
        # Mock file operations to succeed, but git add to fail
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "add"], stderr="Permission denied"
        )

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/test.py",
            content="# Test",
            language="python",
            action=PatchAction.CREATE,
        )

        result = applier.apply_patch(patch)

        assert not result.success
        assert result.error is not None
        assert "Git add failed" in result.error

    def test_create_permission_denied(self, git_worktree):
        """Test handling of permission denied errors."""
        # Make directory read-only
        readonly_dir = git_worktree / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)

        try:
            applier = PatchApplier(git_worktree)
            patch = CodePatch(
                file_path="readonly/test.py",
                content="# Test",
                language="python",
                action=PatchAction.CREATE,
            )

            result = applier.apply_patch(patch)

            # Should fail but not crash
            assert not result.success
            assert result.error is not None
        finally:
            # Cleanup: restore permissions
            os.chmod(readonly_dir, 0o755)


class TestApplyPatchUpdate:
    """Tests for UPDATE patch action."""

    def test_update_existing_file(self, git_worktree):
        """Test updating an existing file."""
        # Create file first
        existing_file = git_worktree / "src/update.py"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_text("# Original")

        # Stage the original file
        subprocess.run(
            ["git", "add", str(existing_file)],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/update.py",
            content="# Updated",
            language="python",
            action=PatchAction.UPDATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert result.warning is None
        assert existing_file.read_text() == "# Updated"

    def test_update_stages_in_git(self, git_worktree):
        """Test that updated file is staged in git."""
        # Create and stage file first
        existing_file = git_worktree / "src/test.py"
        existing_file.parent.mkdir(parents=True, exist_ok=True)
        existing_file.write_text("# Original")
        subprocess.run(
            ["git", "add", str(existing_file)],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/test.py",
            content="# Updated",
            language="python",
            action=PatchAction.UPDATE,
        )

        result = applier.apply_patch(patch)

        assert result.success

        # Check git status
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_worktree,
            capture_output=True,
            text=True,
            check=True,
        )
        assert "src/test.py" in status.stdout

    def test_update_nonexistent_file_warning(self, git_worktree):
        """Test that UPDATE on nonexistent file creates with warning."""
        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/missing.py",
            content="# Created",
            language="python",
            action=PatchAction.UPDATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert result.warning is not None
        assert "does not exist" in result.warning
        assert (git_worktree / "src/missing.py").exists()
        assert (git_worktree / "src/missing.py").read_text() == "# Created"

    def test_update_atomic_write(self, git_worktree):
        """Test that update uses atomic write (temp file + rename)."""
        # Create original file
        target = git_worktree / "src/atomic.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Original")

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/atomic.py",
            content="# New content",
            language="python",
            action=PatchAction.UPDATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        # Verify no temp files left behind
        temp_files = list(target.parent.glob(".weft_tmp_*"))
        assert len(temp_files) == 0

    @patch("os.replace")
    def test_update_atomic_write_cleanup_on_error(self, mock_replace, git_worktree):
        """Test that temp files are cleaned up when write fails."""
        # Create original file
        target = git_worktree / "src/fail.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Original")

        # Make os.replace fail
        mock_replace.side_effect = OSError("Disk full")

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/fail.py",
            content="# Will fail",
            language="python",
            action=PatchAction.UPDATE,
        )

        result = applier.apply_patch(patch)

        assert not result.success
        # Verify no temp files left behind
        temp_files = list(target.parent.glob(".weft_tmp_*"))
        assert len(temp_files) == 0


class TestApplyPatchDelete:
    """Tests for DELETE patch action."""

    def test_delete_existing_file(self, git_worktree):
        """Test deleting an existing file."""
        # Create, stage, and commit file first
        target = git_worktree / "src/delete_me.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# To be deleted")
        subprocess.run(
            ["git", "add", str(target)],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add file to delete"],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/delete_me.py",
            content="",
            language="python",
            action=PatchAction.DELETE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert result.warning is None
        assert not target.exists()

    def test_delete_stages_removal(self, git_worktree):
        """Test that deletion is staged in git."""
        # Create and commit file first
        target = git_worktree / "src/delete_staged.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# To delete")
        subprocess.run(
            ["git", "add", str(target)],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add file to delete"],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/delete_staged.py",
            content="",
            language="python",
            action=PatchAction.DELETE,
        )

        result = applier.apply_patch(patch)

        assert result.success

        # Check git status
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_worktree,
            capture_output=True,
            text=True,
            check=True,
        )
        # File should show as deleted (starts with D)
        assert "D" in status.stdout and "delete_staged.py" in status.stdout

    def test_delete_nonexistent_file_warning(self, git_worktree):
        """Test that deleting nonexistent file succeeds with warning."""
        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/never_existed.py",
            content="",
            language="python",
            action=PatchAction.DELETE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert result.warning is not None
        assert "does not exist" in result.warning

    @patch("subprocess.run")
    def test_delete_git_rm_fails(self, mock_run, git_worktree):
        """Test that git rm failure is handled."""
        # Create file
        target = git_worktree / "src/test.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Test")

        # Make git rm fail
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "rm"], stderr="Permission denied"
        )

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/test.py",
            content="",
            language="python",
            action=PatchAction.DELETE,
        )

        result = applier.apply_patch(patch)

        assert not result.success
        assert result.error is not None
        assert "Git rm failed" in result.error


class TestApplyPatchRouting:
    """Tests for patch action routing."""

    def test_apply_patch_routes_to_create(self, git_worktree):
        """Test that CREATE action routes to _write_file."""
        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/create.py",
            content="# Create",
            language="python",
            action=PatchAction.CREATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert (git_worktree / "src/create.py").exists()

    def test_apply_patch_routes_to_update(self, git_worktree):
        """Test that UPDATE action routes to _write_file."""
        # Create file first
        target = git_worktree / "src/update.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Original")

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/update.py",
            content="# Updated",
            language="python",
            action=PatchAction.UPDATE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert target.read_text() == "# Updated"

    def test_apply_patch_routes_to_delete(self, git_worktree):
        """Test that DELETE action routes to _delete_file."""
        # Create, stage, and commit file
        target = git_worktree / "src/delete.py"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# Delete me")
        subprocess.run(
            ["git", "add", str(target)],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add file to delete"],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )

        applier = PatchApplier(git_worktree)
        patch = CodePatch(
            file_path="src/delete.py",
            content="",
            language="python",
            action=PatchAction.DELETE,
        )

        result = applier.apply_patch(patch)

        assert result.success
        assert not target.exists()


class TestApplyArtifact:
    """Tests for apply_artifact batch operations."""

    def test_apply_artifact_all_succeed(self, git_worktree):
        """Test applying artifact where all patches succeed."""
        patches = [
            CodePatch("src/file1.py", "# File 1", "python", PatchAction.CREATE),
            CodePatch("src/file2.py", "# File 2", "python", PatchAction.CREATE),
            CodePatch("src/file3.py", "# File 3", "python", PatchAction.CREATE),
        ]
        artifact = CodeArtifact(patches=patches, summary="Test artifact")

        applier = PatchApplier(git_worktree)
        results = applier.apply_artifact(artifact)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert (git_worktree / "src/file1.py").exists()
        assert (git_worktree / "src/file2.py").exists()
        assert (git_worktree / "src/file3.py").exists()

    def test_apply_artifact_returns_results(self, git_worktree):
        """Test that apply_artifact returns list of ApplyResult."""
        patches = [
            CodePatch("src/test.py", "# Test", "python", PatchAction.CREATE),
        ]
        artifact = CodeArtifact(patches=patches, summary="Test")

        applier = PatchApplier(git_worktree)
        results = applier.apply_artifact(artifact)

        assert len(results) == 1
        assert isinstance(results[0], ApplyResult)
        assert results[0].file_path == "src/test.py"

    def test_apply_artifact_some_fail_continues(self, git_worktree):
        """Test that apply_artifact continues even when some patches fail."""
        # Create a readonly directory to cause failure
        readonly_dir = git_worktree / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)

        try:
            patches = [
                CodePatch("src/success1.py", "# Success", "python", PatchAction.CREATE),
                CodePatch("readonly/fail.py", "# Fail", "python", PatchAction.CREATE),
                CodePatch("src/success2.py", "# Success", "python", PatchAction.CREATE),
            ]
            artifact = CodeArtifact(patches=patches, summary="Mixed results")

            applier = PatchApplier(git_worktree)
            results = applier.apply_artifact(artifact)

            # All patches attempted
            assert len(results) == 3

            # First and third succeed
            assert results[0].success
            assert not results[1].success  # Middle one fails
            assert results[2].success

            # Successful files exist
            assert (git_worktree / "src/success1.py").exists()
            assert (git_worktree / "src/success2.py").exists()

        finally:
            os.chmod(readonly_dir, 0o755)

    def test_apply_artifact_logs_failures(self, git_worktree, caplog):
        """Test that failures are logged."""
        # Create a patch that will fail
        readonly_dir = git_worktree / "readonly"
        readonly_dir.mkdir()
        os.chmod(readonly_dir, 0o444)

        try:
            patches = [
                CodePatch("readonly/fail.py", "# Fail", "python", PatchAction.CREATE),
            ]
            artifact = CodeArtifact(patches=patches, summary="Will fail")

            applier = PatchApplier(git_worktree)
            applier.apply_artifact(artifact)

            # Check that warning was logged
            assert "Patch failed" in caplog.text
            assert "readonly/fail.py" in caplog.text

        finally:
            os.chmod(readonly_dir, 0o755)

    def test_apply_artifact_empty_patches(self, git_worktree, caplog):
        """Test that empty artifact returns empty list."""
        artifact = CodeArtifact(patches=[], summary="Empty")

        applier = PatchApplier(git_worktree)
        results = applier.apply_artifact(artifact)

        assert results == []
        assert "contains no patches" in caplog.text

    def test_apply_artifact_mixed_actions(self, git_worktree):
        """Test artifact with CREATE, UPDATE, DELETE actions."""
        # Create files to update and delete, then commit
        update_target = git_worktree / "src/update.py"
        update_target.parent.mkdir(parents=True, exist_ok=True)
        update_target.write_text("# Original")

        delete_target = git_worktree / "src/delete.py"
        delete_target.write_text("# To delete")

        # Stage and commit files
        subprocess.run(
            ["git", "add", str(update_target), str(delete_target)],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "Add files for update and delete"],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )

        patches = [
            CodePatch("src/new.py", "# New", "python", PatchAction.CREATE),
            CodePatch("src/update.py", "# Updated", "python", PatchAction.UPDATE),
            CodePatch("src/delete.py", "", "python", PatchAction.DELETE),
        ]
        artifact = CodeArtifact(patches=patches, summary="Mixed actions")

        applier = PatchApplier(git_worktree)
        results = applier.apply_artifact(artifact)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert (git_worktree / "src/new.py").exists()
        assert (git_worktree / "src/update.py").read_text() == "# Updated"
        assert not (git_worktree / "src/delete.py").exists()

    def test_apply_artifact_logging(self, git_worktree, caplog):
        """Test that artifact application is logged."""
        import logging

        caplog.set_level(logging.INFO)

        patches = [
            CodePatch("src/test.py", "# Test", "python", PatchAction.CREATE),
        ]
        artifact = CodeArtifact(patches=patches, summary="Test logging")

        applier = PatchApplier(git_worktree)
        applier.apply_artifact(artifact)

        # Check info logs
        assert "Applying code artifact" in caplog.text
        assert "1 patch(es)" in caplog.text
        assert "Test logging" in caplog.text
        assert "1 succeeded, 0 failed" in caplog.text


class TestIntegration:
    """Integration tests for full workflows."""

    def test_full_workflow_create_update_delete(self, git_worktree):
        """Test complete workflow: create → update → delete."""
        applier = PatchApplier(git_worktree)

        # Step 1: Create
        create_patch = CodePatch(
            "src/lifecycle.py",
            "# Version 1",
            "python",
            PatchAction.CREATE,
        )
        result = applier.apply_patch(create_patch)
        assert result.success
        assert (git_worktree / "src/lifecycle.py").read_text() == "# Version 1"

        # Step 2: Update
        update_patch = CodePatch(
            "src/lifecycle.py",
            "# Version 2",
            "python",
            PatchAction.UPDATE,
        )
        result = applier.apply_patch(update_patch)
        assert result.success
        assert (git_worktree / "src/lifecycle.py").read_text() == "# Version 2"

        # Commit before deleting (git rm requires committed file)
        subprocess.run(
            ["git", "commit", "-m", "Add lifecycle.py"],
            cwd=git_worktree,
            check=True,
            capture_output=True,
        )

        # Step 3: Delete
        delete_patch = CodePatch(
            "src/lifecycle.py",
            "",
            "python",
            PatchAction.DELETE,
        )
        result = applier.apply_patch(delete_patch)
        assert result.success
        assert not (git_worktree / "src/lifecycle.py").exists()

    def test_real_git_worktree_integration(self, git_worktree):
        """Test integration with real git worktree."""
        applier = PatchApplier(git_worktree)

        # Apply multiple patches
        patches = [
            CodePatch("README.md", "# Updated README", "markdown", PatchAction.UPDATE),
            CodePatch("src/main.py", 'print("Hello")', "python", PatchAction.CREATE),
            CodePatch("src/utils.py", "# Utils", "python", PatchAction.CREATE),
        ]

        for code_patch in patches:
            result = applier.apply_patch(code_patch)
            assert result.success

        # Verify git status
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=git_worktree,
            capture_output=True,
            text=True,
            check=True,
        )

        # All files should be staged
        assert "README.md" in status.stdout
        assert "src/main.py" in status.stdout
        assert "src/utils.py" in status.stdout

    def test_apply_result_has_issues_property(self, git_worktree):
        """Test ApplyResult.has_issues property."""
        applier = PatchApplier(git_worktree)

        # Success with no warning
        patch1 = CodePatch("src/clean.py", "# Clean", "python", PatchAction.CREATE)
        result1 = applier.apply_patch(patch1)
        assert not result1.has_issues

        # Success with warning (CREATE on existing file)
        patch2 = CodePatch("src/clean.py", "# Overwrite", "python", PatchAction.CREATE)
        result2 = applier.apply_patch(patch2)
        assert result2.success
        assert result2.has_issues  # Has warning

    def test_concurrent_safe_atomic_writes(self, git_worktree):
        """Test that atomic writes use unique temp file names."""
        applier = PatchApplier(git_worktree)

        # Create multiple files quickly
        patches = [
            CodePatch(f"src/file{i}.py", f"# File {i}", "python", PatchAction.CREATE)
            for i in range(10)
        ]

        # Apply all patches
        for code_patch in patches:
            result = applier.apply_patch(code_patch)
            assert result.success

        # Verify no temp files left behind
        temp_files = list((git_worktree / "src").glob(".weft_tmp_*"))
        assert len(temp_files) == 0

        # Verify all files created
        for i in range(10):
            assert (git_worktree / f"src/file{i}.py").exists()
