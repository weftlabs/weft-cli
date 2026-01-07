"""Tests for Agent 00 Meta using BaseSpecAgent."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from weft.agents import BaseSpecAgent
from weft.queue.models import PromptTask


@pytest.fixture
def mock_meta_config():
    """Mock configuration for meta agent."""
    return {
        "agent_id": "00-meta",
        "agent_name": "meta",
        "spec_filename": "00_meta.md",
        "stage": "specification",
        "order_in_stage": 0,
        "description": "Feature understanding and prompt generation",
        "validation": {"required_sections": []},
    }


@pytest.fixture
def mock_spec_content():
    """Mock spec file content."""
    return """# Agent 00: Meta

**Version:** 1.0.0

## Role

Feature understanding and prompt generation.
"""


class TestMetaAgentInitialization:
    """Tests for Meta agent initialization."""

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_initialization_with_config(
        self, mock_read_text, mock_exists, mock_meta_config, mock_spec_content
    ):
        """Test agent initializes with provided config."""
        mock_exists.return_value = True
        mock_read_text.return_value = mock_spec_content

        backend = Mock()
        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="00-meta",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_meta_config,
        )

        assert agent.feature_id == "feat/test"
        assert agent.agent_id == "00-meta"
        assert agent.agent_name == "meta"
        assert agent.stage == "specification"
        assert agent.backend == backend
        assert agent.spec_version == "1.0.0"

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_initialization_loads_spec(
        self, mock_read_text, mock_exists, mock_meta_config, mock_spec_content
    ):
        """Test agent loads spec file."""
        mock_exists.return_value = True
        mock_read_text.return_value = mock_spec_content

        backend = Mock()
        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="00-meta",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_meta_config,
        )

        assert "Feature understanding" in agent.prompt_spec
        assert agent.spec_version == "1.0.0"


class TestMetaAgentProcessing:
    """Tests for Meta agent prompt processing."""

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_process_prompt_calls_backend(
        self, mock_read_text, mock_exists, mock_meta_config, mock_spec_content
    ):
        """Test processing prompt calls AI backend."""
        mock_exists.return_value = True
        mock_read_text.return_value = mock_spec_content

        backend = Mock()
        backend.generate.return_value = "Generated output"

        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="00-meta",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_meta_config,
        )

        prompt_task = PromptTask(
            feature_id="feat/test",
            agent_id="00-meta",
            prompt_text="Add user authentication",
            spec_version="1.0.0",
            revision=1,
        )

        output = agent.process_prompt(prompt_task)

        assert output == "Generated output"
        backend.generate.assert_called_once()
        call_args = backend.generate.call_args[0][0]
        assert "Add user authentication" in call_args
        assert "meta agent" in call_args.lower()

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_process_prompt_with_empty_text_raises_error(
        self, mock_read_text, mock_exists, mock_meta_config, mock_spec_content
    ):
        """Test processing empty prompt raises ValueError."""
        mock_exists.return_value = True
        mock_read_text.return_value = mock_spec_content

        backend = Mock()
        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="00-meta",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_meta_config,
        )

        prompt_task = PromptTask(
            feature_id="feat/test",
            agent_id="00-meta",
            prompt_text="   ",
            spec_version="1.0.0",
            revision=1,
        )

        with pytest.raises(ValueError, match="cannot be empty"):
            agent.process_prompt(prompt_task)


class TestSpecVersionExtraction:
    """Tests for spec version extraction."""

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_extract_version_from_spec(self, mock_read_text, mock_exists, mock_meta_config):
        """Test version extraction from spec."""
        mock_exists.return_value = True
        spec_with_version = "**Version:** 2.5.3\n\nContent"
        mock_read_text.return_value = spec_with_version

        backend = Mock()
        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="00-meta",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_meta_config,
        )

        assert agent.spec_version == "2.5.3"

    @patch("weft.agents.base_spec_agent.Path.exists")
    @patch("weft.agents.base_spec_agent.Path.read_text")
    def test_default_version_when_not_found(self, mock_read_text, mock_exists, mock_meta_config):
        """Test default version when version not in spec."""
        mock_exists.return_value = True
        spec_without_version = "# Agent spec\n\nNo version here"
        mock_read_text.return_value = spec_without_version

        backend = Mock()
        agent = BaseSpecAgent(
            feature_id="feat/test",
            agent_id="00-meta",
            ai_history_path=Path("/tmp/history"),
            backend=backend,
            config=mock_meta_config,
        )

        assert agent.spec_version == "1.0.0"
