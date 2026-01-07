"""Runtime directory management for .weft/ state."""

from pathlib import Path

from .errors import SecurityError


class WeftRuntime:
    def __init__(self, root: Path = Path(".weft")):
        self.root = root
        self.features = root / "features"
        self.tasks_in = root / "tasks" / "in"
        self.tasks_out = root / "tasks" / "out"
        self.tasks_processed = root / "tasks" / "processed"
        self.history = root / "history"
        self.history_sessions = root / "history" / "sessions"
        self.history_prompts = root / "history" / "prompts"
        self.cache = root / "cache"
        self.prompts = root / "prompts"

    @property
    def base_dir(self) -> Path:
        """Alias for root (backward compatibility)."""
        return self.root

    def initialize(self) -> None:
        """Idempotent setup of directory structure and .gitignore."""
        # Create all directories
        self.root.mkdir(parents=True, exist_ok=True)
        self.features.mkdir(exist_ok=True)
        self.tasks_in.mkdir(parents=True, exist_ok=True)
        self.tasks_out.mkdir(parents=True, exist_ok=True)
        self.tasks_processed.mkdir(parents=True, exist_ok=True)
        self.history.mkdir(exist_ok=True)
        self.history_sessions.mkdir(exist_ok=True)
        self.history_prompts.mkdir(exist_ok=True)
        self.cache.mkdir(exist_ok=True)
        self.prompts.mkdir(exist_ok=True)

        # Create subdirectories for agents
        agents = ["meta", "architect", "openapi", "ui", "integration", "test"]
        for agent in agents:
            (self.tasks_in / agent).mkdir(exist_ok=True)
            (self.tasks_out / agent).mkdir(exist_ok=True)

        # Create .gitignore if it doesn't exist
        self._create_gitignore()

    def _create_gitignore(self) -> None:
        gitignore_path = self.root / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text(
                "# Weft runtime directory\n"
                "# This directory should not be committed to git\n"
                "#\n"
                "# Note: prompts/ is tracked by default for team consistency\n"
                "# Add 'prompts/' below if you prefer to always use weft defaults\n"
                "*\n"
                "!.gitignore\n"
                "!prompts/\n"
            )

    def ensure_no_secrets(self) -> None:
        """Scan for secret patterns in text files."""
        # Scan all files for patterns
        secret_patterns = ["WEFT_", "sk-ant-", "sk-", "api_key", "password"]

        for file_path in self.root.rglob("*"):
            if not file_path.is_file():
                continue

            # Only check text files
            if file_path.suffix not in [".md", ".txt", ".json", ".yaml", ".log"]:
                continue

            try:
                content = file_path.read_text()
                for pattern in secret_patterns:
                    if pattern in content:
                        raise SecurityError(
                            f"Potential secret found in {file_path}\n"
                            f"Pattern: {pattern}\n"
                            f"Secrets must never be written to .weft/\n"
                            f"This is a critical security violation."
                        )
            except UnicodeDecodeError:
                # Skip binary files
                continue

    def exists(self) -> bool:
        return self.root.exists()

    def clean_cache(self) -> None:
        if self.cache.exists():
            for file_path in self.cache.rglob("*"):
                if file_path.is_file():
                    file_path.unlink()

    def get_agent_input_dir(self, agent: str) -> Path:
        return self.tasks_in / agent

    def get_agent_output_dir(self, agent: str) -> Path:
        return self.tasks_out / agent

    def list_agents(self) -> list[str]:
        if not self.tasks_in.exists():
            return []

        return [
            d.name for d in self.tasks_in.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]
