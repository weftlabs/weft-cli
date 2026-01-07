"""Project configuration loading and validation from .weftrc.yaml."""

from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from .errors import ConfigError


class ProjectConfig(BaseModel):
    name: str
    type: str  # backend, frontend, fullstack


class AIConfig(BaseModel):
    provider: str = "anthropic"  # anthropic, openai, local
    model: str = "claude-3-5-sonnet-20241022"  # Specific model to use
    model_profile: str = "standard"  # fast, standard, quality
    history_path: str = "../weft-ai-history"  # Path to AI history repository


class AgentsConfig(BaseModel):
    enabled: list[str] = ["meta", "architect", "openapi", "ui", "integration", "test"]
    disabled: list[str] = []


class GitWorktreeConfig(BaseModel):
    """Git worktree configuration."""

    base_branch: str = "main"
    prefix: str = "feat/"


class GitConfig(BaseModel):
    worktree: GitWorktreeConfig = GitWorktreeConfig()
    ignore_patterns: list[str] = []


class PathsConfig(BaseModel):
    root: str = ".weft"
    features: str = ".weft/features"
    tasks: str = ".weft/tasks"
    history: str = ".weft/history"


class BackendLanguageConfig(BaseModel):
    """Backend language configuration."""

    language: str | None = None
    framework: str | None = None
    package_manager: str | None = None


class FrontendLanguageConfig(BaseModel):
    """Frontend language configuration."""

    language: str | None = None
    framework: str | None = None
    state_management: str | None = None
    ui_library: str | None = None


class TestingLanguageConfig(BaseModel):
    """Testing framework configuration."""

    unit: str | None = None
    integration: str | None = None
    e2e: str | None = None


class DatabaseConfig(BaseModel):
    """Database configuration."""

    type: str | None = None
    orm: str | None = None


class LanguageConfig(BaseModel):
    """Language and framework configuration for code generation."""

    stack: str | None = None
    backend: BackendLanguageConfig | None = None
    frontend: FrontendLanguageConfig | None = None
    testing: TestingLanguageConfig | None = None
    database: DatabaseConfig | None = None


class WeftRC(BaseModel):
    """Complete .weftrc.yaml schema."""

    project: ProjectConfig
    language: LanguageConfig | None = None
    ai: AIConfig = AIConfig()
    agents: AgentsConfig = AgentsConfig()
    git: GitConfig = GitConfig()
    paths: PathsConfig = PathsConfig()


def load_weftrc(path: Path | None = None) -> WeftRC | None:
    """Load and validate .weftrc.yaml file.

    If path not provided, searches for project root first.
    """
    if path is None:
        from weft.utils.project import find_project_root

        project_root = find_project_root()
        if not project_root:
            return None
        path = project_root / ".weftrc.yaml"

    if not path.exists():
        return None

    try:
        with open(path) as f:
            data = yaml.safe_load(f)

        # Check for secrets
        if contains_secrets(data):
            raise ConfigError(
                f"Security violation: Secrets detected in {path}\n"
                "Secrets must be provided via WEFT_* environment variables only.\n"
                "Remove API keys, passwords, or tokens from .weftrc.yaml"
            )

        config = WeftRC(**data)
        validate_weftrc(config)
        return config

    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML in {path}: {e}") from e
    except ValidationError as e:
        raise ConfigError(f"Invalid .weftrc.yaml schema:\n{e}") from e


def contains_secrets(data: dict) -> bool:
    """Check if config contains secret-like values."""
    secret_patterns = [
        "api_key",
        "api-key",
        "apikey",
        "secret",
        "password",
        "token",
        "sk-ant-",
        "sk-",
        "bearer",
    ]

    def check_value(v):
        if isinstance(v, str):
            lower = v.lower()
            return any(pattern in lower for pattern in secret_patterns)
        elif isinstance(v, dict):
            return any(check_value(val) for val in v.values())
        elif isinstance(v, list):
            return any(check_value(item) for item in v)
        return False

    return check_value(data)


def validate_weftrc(config: WeftRC) -> None:
    """Validate .weftrc.yaml configuration."""
    # Validate project type
    valid_types = ["backend", "frontend", "fullstack"]
    if config.project.type not in valid_types:
        raise ConfigError(
            f"Invalid project.type: {config.project.type}\n"
            f"Must be one of: {', '.join(valid_types)}"
        )

    # Validate AI provider
    valid_providers = ["anthropic", "openai", "local"]
    if config.ai.provider not in valid_providers:
        raise ConfigError(
            f"Invalid ai.provider: {config.ai.provider}\n"
            f"Must be one of: {', '.join(valid_providers)}"
        )

    # Validate model profile
    valid_profiles = ["fast", "standard", "quality"]
    if config.ai.model_profile not in valid_profiles:
        raise ConfigError(
            f"Invalid ai.model_profile: {config.ai.model_profile}\n"
            f"Must be one of: {', '.join(valid_profiles)}"
        )

    # Validate agents
    valid_agents = ["meta", "architect", "openapi", "ui", "integration", "test"]
    invalid_enabled = [a for a in config.agents.enabled if a not in valid_agents]
    if invalid_enabled:
        raise ConfigError(
            f"Invalid agents in enabled list: {', '.join(invalid_enabled)}\n"
            f"Valid agents: {', '.join(valid_agents)}"
        )


def create_default_weftrc(
    project_root: Path = Path("."),
    project_name: str = "my-project",
    project_type: str = "backend",
    ai_provider: str = "anthropic",
    model: str = "claude-3-5-sonnet-20241022",
    ai_history_path: str = "../weft-ai-history",
) -> WeftRC:
    """Create a .weftrc.yaml file with custom configuration."""
    # Determine which agents to enable based on project type
    if project_type == "backend":
        # Backend: API specs and tests, no UI
        enabled_agents = ["meta", "architect", "openapi", "test"]
    elif project_type == "frontend":
        # Frontend: UI components, API integration, tests (no OpenAPI generation)
        enabled_agents = ["meta", "architect", "ui", "integration", "test"]
    else:  # fullstack
        # Fullstack: All agents
        enabled_agents = ["meta", "architect", "openapi", "ui", "integration", "test"]

    config = WeftRC(
        project=ProjectConfig(name=project_name, type=project_type),
        ai=AIConfig(provider=ai_provider, model=model, history_path=ai_history_path),
        agents=AgentsConfig(enabled=enabled_agents),
    )

    # Write to file
    weftrc_path = project_root / ".weftrc.yaml"
    with open(weftrc_path, "w") as f:
        yaml.dump(config.model_dump(), f, default_flow_style=False, sort_keys=False)

    return config
