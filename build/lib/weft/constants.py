"""System-wide constants for Weft CLI.

This module defines all magic numbers, default values, and system constants
used throughout the Weft codebase.
"""

# Agent configuration
AGENT_IDS = (
    "00-meta",
    "01-architect",
    "02-openapi",
    "03-ui",
    "04-integration",
    "05-test",
)

AGENT_NAMES = {
    "00-meta": "Meta",
    "01-architect": "Architect",
    "02-openapi": "OpenAPI",
    "03-ui": "UI",
    "04-integration": "Integration",
    "05-test": "Test",
}

# Agent execution stages
AGENT_STAGES = [
    "specification",  # Understand and specify requirements
    "architecture",  # Design system architecture
    "implementation",  # Build concrete components
    "validation",  # Test and verify implementation
]

# Timing configuration (in seconds)
DEFAULT_POLL_INTERVAL = 2
DEFAULT_TIMEOUT = 300  # 5 minutes
AI_REQUEST_TIMEOUT = 60  # 1 minute

# AI configuration
DEFAULT_MAX_TOKENS = 4096
DEFAULT_MAX_RETRIES = 3

# Feature state ordering for display (priority order)
FEATURE_STATE_ORDER = {
    "in-progress": 0,
    "draft": 1,
    "ready": 2,
    "review": 3,
    "completed": 4,
    "dropped": 5,
}

# Prompt specification versioning
DEFAULT_PROMPT_VERSION = "v1.0.0"

# Git configuration
DEFAULT_BASE_BRANCH = "main"
DEFAULT_BRANCH_PREFIX = "feat/"

# File patterns
YAML_FRONTMATTER_DELIMITER = "---"
MARKDOWN_CODE_FENCE = "```"
