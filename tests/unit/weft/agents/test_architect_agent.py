"""Tests for Agent 01 Architect using BaseSpecAgent."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from weft.agents import BaseSpecAgent
from weft.queue.models import PromptTask


@pytest.fixture
def mock_architect_config():
    """Mock configuration for architect agent."""
    return {
        "agent_id": "01-architect",
        "agent_name": "architect",
        "spec_filename": "01_architect.md",
        "stage": "architecture",
        "order_in_stage": 0,
        "description": "Domain modeling and technical architecture",
        "validation": {
            "required_sections": [
                "## Domain Model",
                "## Use Cases",
                "## API Requirements",
                "## Data Flow",
                "## Trade-offs",
            ]
        },
    }


@pytest.fixture
def mock_spec_content():
    """Mock spec file content."""
    return """# Agent 01: Architect

**Version:** 1.0.0

## Role

Domain modeling and technical architecture design.
"""


class TestArchitectAgentInitialization:
    """Tests for Architect agent initialization."""

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_initialization_with_config(
        self, mock_read_text, mock_exists, mock_architect_config, mock_spec_content
    ):
        """Test agent initializes with provided config."""
        mock_exists.return_value = True
        mock_read_text.return_value = mock_spec_content

        backend = Mock()
        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="01-architect",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_architect_config,
        )

        assert agent.feature_id == "feat/test"
        assert agent.agent_id == "01-architect"
        assert agent.agent_name == "architect"
        assert agent.stage == "architecture"
        assert agent.backend == backend
        assert agent.spec_version == "1.0.0"


class TestArchitectAgentProcessing:
    """Tests for Architect agent prompt processing."""

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_process_prompt_with_valid_output(
        self, mock_read_text, mock_exists, mock_architect_config, mock_spec_content
    ):
        """Test processing prompt with valid output."""
        mock_exists.return_value = True
        mock_read_text.return_value = mock_spec_content

        backend = Mock()
        backend.generate.return_value = """# Technical Design

## Domain Model
User entity with fields.

## Use Cases
- UC1: User login

## API Requirements
- POST /auth/login

## Data Flow
Request -> Validate -> Response

## Trade-offs
JWT vs sessions
"""

        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="01-architect",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_architect_config,
        )

        prompt_task = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Design authentication architecture",
            spec_version="1.0.0",
            revision=1,
        )

        output = agent.process_prompt(prompt_task)

        assert "Domain Model" in output
        assert "Use Cases" in output
        assert "API Requirements" in output
        backend.generate.assert_called_once()

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_process_prompt_with_missing_sections_raises_error(
        self, mock_read_text, mock_exists, mock_architect_config, mock_spec_content
    ):
        """Test processing prompt with incomplete output raises ValueError."""
        mock_exists.return_value = True
        mock_read_text.return_value = mock_spec_content

        backend = Mock()
        backend.generate.return_value = """# Technical Design

## Domain Model
Just a domain model, missing other sections.
"""

        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="01-architect",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_architect_config,
        )

        prompt_task = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Design authentication architecture",
            spec_version="1.0.0",
            revision=1,
        )

        with pytest.raises(ValueError, match="missing required sections"):
            agent.process_prompt(prompt_task)


class TestOutputValidation:
    """Tests for output validation."""

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_validation_passes_with_all_sections(
        self, mock_read_text, mock_exists, mock_architect_config, mock_spec_content
    ):
        """Test validation passes when all sections present."""
        mock_exists.return_value = True
        mock_read_text.return_value = mock_spec_content

        backend = Mock()
        backend.generate.return_value = """
## Domain Model
Model

## Use Cases
Cases

## API Requirements
API

## Data Flow
Flow

## Trade-offs
Trade
"""

        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="01-architect",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_architect_config,
        )

        prompt_task = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Design",
            spec_version="1.0.0",
            revision=1,
        )

        # Should not raise
        output = agent.process_prompt(prompt_task)
        assert output is not None

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_validation_skipped_when_no_rules(self, mock_read_text, mock_exists, mock_spec_content):
        """Test validation is skipped when no validation rules."""
        mock_exists.return_value = True
        mock_read_text.return_value = mock_spec_content

        # Config without validation rules
        config_no_validation = {
            "agent_id": "01-architect",
            "agent_name": "architect",
            "spec_filename": "01_architect.md",
            "stage": "architecture",
            "order_in_stage": 0,
            "description": "Domain modeling",
            "validation": {},  # No required_sections
        }

        backend = Mock()
        backend.generate.return_value = "Any output"

        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="01-architect",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=config_no_validation,
        )

        prompt_task = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Design",
            spec_version="1.0.0",
            revision=1,
        )

        # Should not raise even with incomplete output
        output = agent.process_prompt(prompt_task)
        assert output == "Any output"
