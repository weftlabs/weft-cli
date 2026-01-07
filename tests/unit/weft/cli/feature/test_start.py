"""Tests for feature start command with agent orchestration."""

import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from weft.cli.feature.start import AgentOrchestrator, feature_start


@pytest.mark.timeout(30)
class TestAgentOrchestrator:
    """Tests for AgentOrchestrator class."""

    def test_build_agent_graph_order(self, tmp_path: Path):
        """Test agent execution order from enabled agents."""
        ai_history = tmp_path / "ai-history"
        enabled_agents = ["00-meta", "01-architect", "02-openapi"]

        orchestrator = AgentOrchestrator(
            feature_name="test-feature",
            ai_history_path=ai_history,
            enabled_agents=enabled_agents,
        )

        assert orchestrator.agents == ["00-meta", "01-architect", "02-openapi"]

    def test_generate_agent_input_meta(self, tmp_path: Path):
        """Test generating input for meta agent reads spec."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        # Create spec file
        meta_out = ai_history / feature_id / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "test_result.md").write_text("# Spec Content")

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["00-meta"])

        result = orchestrator._generate_agent_input("00-meta")

        assert result == "# Spec Content"

    def test_generate_agent_input_meta_missing_spec(self, tmp_path: Path):
        """Test meta agent input generation fails if spec missing."""
        ai_history = tmp_path / "ai-history"

        orchestrator = AgentOrchestrator("test", ai_history, ["00-meta"])

        with pytest.raises(FileNotFoundError, match="Spec not found"):
            orchestrator._generate_agent_input("00-meta")

    def test_generate_agent_input_architect(self, tmp_path: Path):
        """Test architect agent receives meta's output."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        # Create meta spec
        meta_out = ai_history / feature_id / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "meta_result.md").write_text("# Meta Output")

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["01-architect"])

        result = orchestrator._generate_agent_input("01-architect")

        assert result == "# Meta Output"

    def test_generate_agent_input_openapi(self, tmp_path: Path):
        """Test OpenAPI agent receives architect's output."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        # Create meta output (required for extracting agent prompts)
        meta_out = ai_history / feature_id / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "meta_result.md").write_text("# Meta\n\n## 02-openapi\nOpenAPI prompt")

        # Create architect output
        architect_out = ai_history / feature_id / "01-architect" / "out"
        architect_out.mkdir(parents=True)
        (architect_out / "architect_result.md").write_text("# Architect Output")

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["02-openapi"])

        result = orchestrator._generate_agent_input("02-openapi")

        assert "OpenAPI prompt" in result
        assert "# Architect Output" in result

    def test_generate_agent_input_ui_combines_outputs(self, tmp_path: Path):
        """Test UI agent receives architect + openapi outputs."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        # Create meta output (required for extracting agent prompts)
        meta_out = ai_history / feature_id / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "meta_result.md").write_text("# Meta\n\n## 03-ui\nUI prompt")

        # Create architect output
        architect_out = ai_history / feature_id / "01-architect" / "out"
        architect_out.mkdir(parents=True)
        (architect_out / "architect_result.md").write_text("Arch content")

        # Create openapi output
        openapi_out = ai_history / feature_id / "02-openapi" / "out"
        openapi_out.mkdir(parents=True)
        (openapi_out / "openapi_result.md").write_text("API content")

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["03-ui"])

        result = orchestrator._generate_agent_input("03-ui")

        assert "UI prompt" in result
        assert "Arch content" in result
        assert "API content" in result

    def test_submit_to_agent_creates_prompt_file(self, tmp_path: Path):
        """Test submitting creates prompt in agent's input directory."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["00-meta"])

        prompt_file = orchestrator._submit_to_agent("00-meta", "Test prompt")

        assert prompt_file.exists()
        assert prompt_file.name.endswith("_prompt.md")  # Timestamp-based naming
        assert "Test prompt" in prompt_file.read_text()

    def test_wait_for_agent_success(self, tmp_path: Path):
        """Test waiting successfully finds agent output."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        # Create output directory
        output_dir = ai_history / feature_id / "00-meta" / "out"
        output_dir.mkdir(parents=True)

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["00-meta"])

        # Create file in separate thread after short delay to ensure timestamp is after wait starts
        def create_result():
            time.sleep(0.5)
            (output_dir / "test_result.md").write_text("Result content")

        import threading

        thread = threading.Thread(target=create_result, daemon=True)
        thread.start()

        # Should find the result
        result = orchestrator._wait_for_agent("00-meta", timeout=5)

        thread.join()
        assert result is True

    def test_wait_for_agent_timeout(self, tmp_path: Path):
        """Test waiting times out when no output."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        # Create output directory but no file
        output_dir = ai_history / feature_id / "00-meta" / "out"
        output_dir.mkdir(parents=True)

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["00-meta"])

        result = orchestrator._wait_for_agent("00-meta", timeout=1)

        assert result is False

    def test_handle_agent_failure_retry_success(self, tmp_path: Path, monkeypatch):
        """Test retrying after failure succeeds."""
        ai_history = tmp_path / "ai-history"
        orchestrator = AgentOrchestrator("test", ai_history, ["00-meta"])

        # Mock user choosing retry
        monkeypatch.setattr("click.prompt", lambda *args, **kwargs: "retry")

        # Mock wait succeeding on retry
        def mock_wait(agent, timeout=600):
            return True

        orchestrator._wait_for_agent = mock_wait

        result = orchestrator._handle_agent_failure("00-meta")

        assert result is True

    def test_handle_agent_failure_skip(self, tmp_path: Path, monkeypatch):
        """Test skipping failed agent continues."""
        ai_history = tmp_path / "ai-history"
        orchestrator = AgentOrchestrator("test", ai_history, ["00-meta"])

        # Mock user choosing skip
        monkeypatch.setattr("click.prompt", lambda *args, **kwargs: "skip")

        result = orchestrator._handle_agent_failure("00-meta")

        assert result is True

    def test_handle_agent_failure_abort(self, tmp_path: Path, monkeypatch):
        """Test aborting stops processing."""
        ai_history = tmp_path / "ai-history"
        orchestrator = AgentOrchestrator("test", ai_history, ["00-meta"])

        # Mock user choosing abort
        monkeypatch.setattr("click.prompt", lambda *args, **kwargs: "abort")

        result = orchestrator._handle_agent_failure("00-meta")

        assert result is False

    @patch.object(AgentOrchestrator, "_wait_for_agent")
    def test_run_single_agent(self, mock_wait, tmp_path: Path):
        """Test running specific agent only."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        # Create spec for meta
        meta_out = ai_history / feature_id / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "spec_result.md").write_text("# Spec")

        # Mock wait to return success immediately
        mock_wait.return_value = True

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["00-meta", "01-architect"])

        result = orchestrator.run(specific_agent="01-architect")

        # Should create prompt for architect
        prompt_dir = ai_history / feature_id / "01-architect" / "in"
        assert prompt_dir.exists()
        prompts = list(prompt_dir.glob("*_prompt.md"))
        assert len(prompts) == 1

        # Should succeed
        assert result is True

    @patch.object(AgentOrchestrator, "_wait_for_agent")
    def test_run_all_agents_sequence(self, mock_wait, tmp_path: Path):
        """Test running all agents in sequence."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        # Create spec file
        meta_out = ai_history / feature_id / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "spec_result.md").write_text("# Spec")

        # Mock wait to return success immediately
        mock_wait.return_value = True

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["00-meta", "01-architect"])

        result = orchestrator.run()

        # Should create prompts for both agents (timestamp-based naming)
        meta_prompts = list((ai_history / feature_id / "00-meta" / "in").glob("*_prompt.md"))
        arch_prompts = list((ai_history / feature_id / "01-architect" / "in").glob("*_prompt.md"))

        assert len(meta_prompts) == 1
        assert len(arch_prompts) == 1

        assert result is True

    def test_run_stops_on_failure_abort(self, tmp_path: Path, monkeypatch):
        """Test run stops when user aborts after failure."""
        ai_history = tmp_path / "ai-history"
        feature_id = "test-feature"

        # Create spec but no architect output (will fail)
        meta_out = ai_history / feature_id / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "spec.md").write_text("# Spec")

        # Create architect output dir but no file (will timeout)
        architect_out = ai_history / feature_id / "01-architect" / "out"
        architect_out.mkdir(parents=True)

        # Mock user choosing abort
        monkeypatch.setattr("click.prompt", lambda *args, **kwargs: "abort")

        orchestrator = AgentOrchestrator(feature_id, ai_history, ["00-meta", "01-architect"])

        # Should stop after meta times out and user aborts
        result = orchestrator.run()

        assert result is False


@pytest.mark.timeout(30)
class TestFeatureStartCommand:
    """Tests for feature-start CLI command."""

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.start.load_weftrc")
    @patch.object(AgentOrchestrator, "_wait_for_agent")
    def test_feature_start_all_agents(
        self, mock_wait, mock_load_weftrc, mock_settings, tmp_path: Path
    ):
        """Test starting all agents for feature."""
        # Setup mocks
        mock_settings.return_value = Mock(
            ai_history_path=tmp_path / "ai-history",
        )

        mock_config = Mock()
        mock_config.agents.enabled = ["00-meta", "01-architect"]
        mock_load_weftrc.return_value = mock_config

        # Mock wait to return success immediately
        mock_wait.return_value = True

        # Create spec file that the CLI expects
        ai_history = tmp_path / "ai-history"
        meta_out = ai_history / "test-feature" / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "spec_result.md").write_text("# Feature Spec")

        runner = CliRunner()
        result = runner.invoke(feature_start, ["test-feature"])

        assert result.exit_code == 0
        assert "Starting agent pipeline" in result.output
        assert "00-meta" in result.output
        assert "01-architect" in result.output
        assert "processing complete" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.start.load_weftrc")
    @patch.object(AgentOrchestrator, "_wait_for_agent")
    def test_feature_start_specific_agent(
        self, mock_wait, mock_load_weftrc, mock_settings, tmp_path: Path
    ):
        """Test starting specific agent only."""
        mock_settings.return_value = Mock(
            ai_history_path=tmp_path / "ai-history",
        )

        mock_config = Mock()
        mock_config.agents.enabled = ["00-meta", "01-architect"]
        mock_load_weftrc.return_value = mock_config

        # Mock wait to return success immediately
        mock_wait.return_value = True

        # Create spec file that the CLI expects
        ai_history = tmp_path / "ai-history"
        meta_out = ai_history / "test-feature" / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "spec_result.md").write_text("# Feature Spec")

        runner = CliRunner()
        result = runner.invoke(feature_start, ["test-feature", "--agent", "architect"])

        assert result.exit_code == 0
        assert "Running single agent: 01-architect" in result.output
        assert "01-architect completed" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.start.load_weftrc")
    def test_feature_start_agent_not_enabled(self, mock_load_weftrc, mock_settings, tmp_path: Path):
        """Test error when requested agent not enabled."""
        mock_settings.return_value = Mock(
            ai_history_path=tmp_path / "ai-history",
        )

        mock_config = Mock()
        mock_config.agents.enabled = ["00-meta"]
        mock_load_weftrc.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(feature_start, ["test-feature", "--agent", "architect"])

        assert result.exit_code != 0
        assert "not enabled" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.start.load_weftrc")
    def test_feature_start_no_spec(self, mock_load_weftrc, mock_settings, tmp_path: Path):
        """Test error when spec doesn't exist."""
        mock_settings.return_value = Mock(
            ai_history_path=tmp_path / "ai-history",
        )

        mock_config = Mock()
        mock_config.agents.enabled = ["00-meta"]
        mock_load_weftrc.return_value = mock_config

        runner = CliRunner()
        result = runner.invoke(feature_start, ["test-feature"])

        assert result.exit_code != 0
        assert "Spec not found" in result.output or "Error:" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.start.load_weftrc")
    def test_feature_start_no_weftrc(self, mock_load_weftrc, mock_settings):
        """Test error when .weftrc.yaml not found."""
        mock_settings.return_value = Mock(
            ai_history_path=Path("/tmp/ai-history"),
        )
        mock_load_weftrc.return_value = None

        runner = CliRunner()
        result = runner.invoke(feature_start, ["test-feature"])

        assert result.exit_code != 0
        assert ".weftrc.yaml not found" in result.output

    @patch("weft.cli.utils.get_settings")
    def test_feature_start_settings_error(self, mock_settings):
        """Test error when settings cannot be loaded."""
        mock_settings.side_effect = ValueError("Settings missing")

        runner = CliRunner()
        result = runner.invoke(feature_start, ["test-feature"])

        assert result.exit_code != 0
        assert "Settings missing" in result.output

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.start.load_weftrc")
    @patch.object(AgentOrchestrator, "_wait_for_agent")
    def test_feature_start_agent_name_normalization(
        self, mock_wait, mock_load_weftrc, mock_settings, tmp_path: Path
    ):
        """Test agent name normalization from friendly names."""
        mock_settings.return_value = Mock(
            ai_history_path=tmp_path / "ai-history",
        )

        mock_config = Mock()
        mock_config.agents.enabled = ["00-meta", "01-architect"]
        mock_load_weftrc.return_value = mock_config

        # Mock wait to return success immediately
        mock_wait.return_value = True

        # Create spec file that the CLI expects
        ai_history = tmp_path / "ai-history"
        meta_out = ai_history / "test-feature" / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "spec_result.md").write_text("# Feature Spec")

        runner = CliRunner()

        # Test with friendly name "architect" instead of "01-architect"
        result = runner.invoke(feature_start, ["test-feature", "-a", "architect"])

        assert result.exit_code == 0
        assert "01-architect" in result.output


@pytest.mark.timeout(30)
class TestFeatureStartIntegration:
    """Integration tests for feature start workflow."""

    @patch("weft.cli.utils.get_settings")
    @patch("weft.cli.feature.start.load_weftrc")
    @patch.object(AgentOrchestrator, "_wait_for_agent")
    def test_full_pipeline_workflow(
        self, mock_wait, mock_load_weftrc, mock_settings, tmp_path: Path
    ):
        """Test complete pipeline from meta to test."""
        mock_settings.return_value = Mock(
            ai_history_path=tmp_path / "ai-history",
        )

        mock_config = Mock()
        mock_config.agents.enabled = ["00-meta", "01-architect", "02-openapi"]
        mock_load_weftrc.return_value = mock_config

        ai_history = tmp_path / "ai-history"
        feature_id = "user-auth"

        # Create initial spec file
        meta_out = ai_history / feature_id / "00-meta" / "out"
        meta_out.mkdir(parents=True)
        (meta_out / "spec_result.md").write_text("# Feature Spec")

        # Mock wait to create output files dynamically as agents "complete"
        def mock_wait_side_effect(agent, timeout=600, min_timestamp=None):
            # Create output file for the agent that just "completed"
            out_dir = ai_history / feature_id / agent / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            (out_dir / f"{agent}_result.md").write_text(f"# {agent} output")
            return True

        mock_wait.side_effect = mock_wait_side_effect

        runner = CliRunner()
        result = runner.invoke(feature_start, [feature_id])

        if result.exit_code != 0:
            print(f"Output: {result.output}")

        assert result.exit_code == 0

        # Verify prompts were created for all agents (timestamp-based naming)
        for agent in ["00-meta", "01-architect", "02-openapi"]:
            prompts = list((ai_history / feature_id / agent / "in").glob("*_prompt.md"))
            assert len(prompts) > 0, f"No prompts found for {agent}"

        # Verify output messages
        assert "00-meta completed" in result.output
        assert "01-architect completed" in result.output
        assert "02-openapi completed" in result.output
        assert "processing complete" in result.output
