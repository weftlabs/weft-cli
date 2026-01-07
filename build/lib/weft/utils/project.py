"""Project root discovery utilities."""

from pathlib import Path

from weft.config.errors import ConfigError


def find_project_root(start_path: Path | None = None) -> Path | None:
    """Searches for .weftrc.yaml (primary) or .weft/ directory (fallback)."""
    current = start_path or Path.cwd()
    current = current.resolve()

    while True:
        if (current / ".weftrc.yaml").exists():
            return current

        if (current / ".weft").is_dir():
            return current

        parent = current.parent
        if parent == current:
            return None

        current = parent


def get_project_root() -> Path:
    root = find_project_root()
    if root is None:
        cwd = Path.cwd()
        raise ConfigError(
            f"Not in a weft project (searched from {cwd})\n"
            "Run 'weft init' to initialize a project"
        )
    return root
