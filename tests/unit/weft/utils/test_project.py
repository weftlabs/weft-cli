"""Tests for project root discovery."""

from pathlib import Path

import pytest

from weft.config.errors import ConfigError
from weft.utils.project import find_project_root, get_project_root


class TestFindProjectRoot:
    """Tests for find_project_root function."""

    def test_finds_weftrc_in_current_directory(self, tmp_path: Path, monkeypatch):
        """Test finding .weftrc.yaml in current directory."""
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")

        monkeypatch.chdir(tmp_path)
        result = find_project_root()

        assert result == tmp_path

    def test_finds_weftrc_in_parent_directory(self, tmp_path: Path, monkeypatch):
        """Test finding .weftrc.yaml in parent directory."""
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        subdir = tmp_path / "src"
        subdir.mkdir()

        monkeypatch.chdir(subdir)
        result = find_project_root()

        assert result == tmp_path

    def test_finds_weftrc_in_nested_parent(self, tmp_path: Path, monkeypatch):
        """Test finding .weftrc.yaml multiple levels up."""
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        deep_dir = tmp_path / "src" / "deep" / "nested"
        deep_dir.mkdir(parents=True)

        monkeypatch.chdir(deep_dir)
        result = find_project_root()

        assert result == tmp_path

    def test_finds_weft_directory(self, tmp_path: Path, monkeypatch):
        """Test finding .weft/ directory as fallback."""
        weft_dir = tmp_path / ".weft"
        weft_dir.mkdir()

        monkeypatch.chdir(tmp_path)
        result = find_project_root()

        assert result == tmp_path

    def test_prefers_weftrc_over_weft_dir(self, tmp_path: Path, monkeypatch):
        """Test that .weftrc.yaml is preferred over .weft/ directory."""
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / ".weft").mkdir()

        monkeypatch.chdir(tmp_path)
        result = find_project_root()

        assert result == tmp_path

    def test_returns_none_when_not_found(self, tmp_path: Path, monkeypatch):
        """Test returns None when no project root found."""
        monkeypatch.chdir(tmp_path)
        result = find_project_root()

        assert result is None

    def test_accepts_explicit_start_path(self, tmp_path: Path):
        """Test can provide explicit start path."""
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        subdir = tmp_path / "src"
        subdir.mkdir()

        result = find_project_root(start_path=subdir)

        assert result == tmp_path

    def test_resolves_symlinks(self, tmp_path: Path, monkeypatch):
        """Test handles symlinks correctly."""
        project_root = tmp_path / "project"
        project_root.mkdir()
        (project_root / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")

        # Create symlink to subdirectory
        subdir = project_root / "src"
        subdir.mkdir()
        link = tmp_path / "link"
        link.symlink_to(subdir)

        monkeypatch.chdir(link)
        result = find_project_root()

        assert result == project_root.resolve()


class TestGetProjectRoot:
    """Tests for get_project_root function."""

    def test_returns_project_root_when_found(self, tmp_path: Path, monkeypatch):
        """Test returns project root when found."""
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")

        monkeypatch.chdir(tmp_path)
        result = get_project_root()

        assert result == tmp_path

    def test_raises_error_when_not_found(self, tmp_path: Path, monkeypatch):
        """Test raises ConfigError when not in a project."""
        monkeypatch.chdir(tmp_path)

        with pytest.raises(ConfigError) as exc_info:
            get_project_root()

        assert "Not in a weft project" in str(exc_info.value)
        assert str(tmp_path) in str(exc_info.value)
        assert "weft init" in str(exc_info.value)

    def test_works_from_subdirectory(self, tmp_path: Path, monkeypatch):
        """Test get_project_root works from subdirectory."""
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        subdir = tmp_path / "src" / "nested"
        subdir.mkdir(parents=True)

        monkeypatch.chdir(subdir)
        result = get_project_root()

        assert result == tmp_path
