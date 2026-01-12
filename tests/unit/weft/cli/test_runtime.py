"""Tests for runtime management commands."""

from pathlib import Path
from unittest.mock import Mock, patch

import yaml
from click.testing import CliRunner

from weft.cli.runtime import down, logs, up
from weft.cli.runtime.helpers import validate_docker


class TestValidateDocker:
    """Tests for docker validation."""

    @patch("subprocess.run")
    def test_validate_docker_success(self, mock_run):
        """Test successful docker validation."""
        mock_run.return_value = Mock(returncode=0)

        assert validate_docker() is True
        assert mock_run.call_count == 2  # docker --version and docker compose version

    @patch("subprocess.run")
    def test_validate_docker_not_installed(self, mock_run):
        """Test docker not installed."""
        mock_run.side_effect = FileNotFoundError()

        assert validate_docker() is False

    @patch("subprocess.run")
    def test_validate_docker_compose_missing(self, mock_run):
        """Test docker installed but compose missing."""
        # First call (docker --version) succeeds, second fails
        mock_run.side_effect = [
            Mock(returncode=0),
            FileNotFoundError(),
        ]

        assert validate_docker() is False


class TestUpCommand:
    """Tests for 'weft up' command."""

    @patch("subprocess.run")
    @patch("weft.cli.runtime.up.validate_docker")
    @patch("weft.cli.runtime.up.check_docker_daemon")
    @patch("weft.cli.runtime.up.load_weftrc")
    def test_up_success(
        self,
        mock_load_config,
        mock_check_daemon,
        mock_validate,
        mock_run,
        tmp_path: Path,
        monkeypatch,
    ):
        """Test successful 'weft up' command."""
        monkeypatch.chdir(tmp_path)

        # Create project markers
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\nservices:\n  test: {}\n")

        # Mock config with enabled agents
        mock_config = Mock()
        mock_config.agents.enabled = ["meta", "architect"]
        mock_load_config.return_value = mock_config

        mock_validate.return_value = True
        mock_check_daemon.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(up)

        assert result.exit_code == 0
        assert "Starting Weft runtime" in result.output
        assert "meta, architect" in result.output
        assert "Runtime started successfully" in result.output

        # Verify docker compose command was called with correct services
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "compose" in call_args
        assert "up" in call_args
        assert "-d" in call_args
        assert "watcher-meta" in call_args
        assert "watcher-architect" in call_args

    @patch("weft.cli.runtime.up.validate_docker")
    def test_up_docker_not_installed(self, mock_validate, tmp_path: Path, monkeypatch):
        """Test 'weft up' when docker not installed."""
        monkeypatch.chdir(tmp_path)
        mock_validate.return_value = False

        runner = CliRunner()
        result = runner.invoke(up)

        assert result.exit_code != 0
        assert "Docker is not installed" in result.output
        assert "https://docs.docker.com" in result.output

    @patch("weft.cli.runtime.up.validate_docker")
    @patch("weft.cli.runtime.up.check_docker_daemon")
    def test_up_docker_daemon_not_running(
        self, mock_check_daemon, mock_validate, tmp_path: Path, monkeypatch
    ):
        """Test 'weft up' when docker daemon not running."""
        monkeypatch.chdir(tmp_path)
        mock_validate.return_value = True
        mock_check_daemon.return_value = False

        runner = CliRunner()
        result = runner.invoke(up)

        assert result.exit_code != 0
        assert "Docker daemon is not running" in result.output

    @patch("weft.cli.runtime.up.validate_docker")
    @patch("weft.cli.runtime.up.check_docker_daemon")
    @patch("weft.cli.runtime.up.load_weftrc")
    def test_up_no_weftrc(
        self, mock_load_config, mock_check_daemon, mock_validate, tmp_path: Path, monkeypatch
    ):
        """Test 'weft up' when .weftrc.yaml not found."""
        monkeypatch.chdir(tmp_path)
        mock_validate.return_value = True
        mock_check_daemon.return_value = True
        mock_load_config.return_value = None

        runner = CliRunner()
        result = runner.invoke(up)

        assert result.exit_code != 0
        assert ".weftrc.yaml not found" in result.output
        assert "weft init" in result.output

    @patch("subprocess.run")
    @patch("weft.cli.runtime.up.validate_docker")
    @patch("weft.cli.runtime.up.check_docker_daemon")
    @patch("weft.cli.runtime.up.load_weftrc")
    def test_up_no_detach_flag(
        self,
        mock_load_config,
        mock_check_daemon,
        mock_validate,
        mock_run,
        tmp_path: Path,
        monkeypatch,
    ):
        """Test 'weft up --no-detach' runs in foreground."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        mock_config = Mock()
        mock_config.agents.enabled = ["meta"]
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True
        mock_check_daemon.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(up, ["--no-detach"])

        assert result.exit_code == 0

        # Verify -d flag is NOT included
        call_args = mock_run.call_args[0][0]
        assert "-d" not in call_args


class TestDownCommand:
    """Tests for 'weft down' command."""

    @patch("subprocess.run")
    @patch("weft.cli.runtime.down.validate_docker")
    def test_down_success(self, mock_validate, mock_run, tmp_path: Path, monkeypatch):
        """Test successful 'weft down' command."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        mock_validate.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(down)

        assert result.exit_code == 0
        assert "Stopping Weft runtime" in result.output
        assert "Runtime stopped successfully" in result.output

        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "compose" in call_args
        assert "-f" in call_args
        assert "down" in call_args

    @patch("subprocess.run")
    @patch("weft.cli.runtime.down.validate_docker")
    def test_down_with_volumes(self, mock_validate, mock_run, tmp_path: Path, monkeypatch):
        """Test 'weft down --volumes' removes volumes."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        mock_validate.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(down, ["--volumes"])

        assert result.exit_code == 0

        call_args = mock_run.call_args[0][0]
        assert "--volumes" in call_args

    @patch("weft.cli.runtime.down.validate_docker")
    def test_down_docker_not_installed(self, mock_validate, tmp_path: Path, monkeypatch):
        """Test 'weft down' when docker not installed."""
        monkeypatch.chdir(tmp_path)
        mock_validate.return_value = False

        runner = CliRunner()
        result = runner.invoke(down)

        assert result.exit_code != 0
        assert "Docker is not installed" in result.output


class TestLogsCommand:
    """Tests for 'weft logs' command."""

    @patch("subprocess.run")
    @patch("weft.cli.runtime.logs.validate_docker")
    def test_logs_specific_agent(self, mock_validate, mock_run, tmp_path: Path, monkeypatch):
        """Test 'weft logs <agent>' for specific agent."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        mock_validate.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(logs, ["meta"])

        assert result.exit_code == 0
        assert "Logs for watcher-meta" in result.output

        call_args = mock_run.call_args[0][0]
        assert "docker" in call_args
        assert "compose" in call_args
        assert "logs" in call_args
        assert "watcher-meta" in call_args

    @patch("subprocess.run")
    @patch("weft.cli.runtime.logs.validate_docker")
    def test_logs_all_services(self, mock_validate, mock_run, tmp_path: Path, monkeypatch):
        """Test 'weft logs' without agent shows all services."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        mock_validate.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(logs)

        assert result.exit_code == 0
        assert "Logs for all services" in result.output

        call_args = mock_run.call_args[0][0]
        # Should not have specific service
        assert "watcher-" not in " ".join(call_args)

    @patch("subprocess.run")
    @patch("weft.cli.runtime.logs.validate_docker")
    def test_logs_follow_flag(self, mock_validate, mock_run, tmp_path: Path, monkeypatch):
        """Test 'weft logs --follow' streams logs."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        mock_validate.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(logs, ["meta", "--follow"])

        assert result.exit_code == 0

        call_args = mock_run.call_args[0][0]
        assert "--follow" in call_args

    @patch("subprocess.run")
    @patch("weft.cli.runtime.logs.validate_docker")
    def test_logs_tail_option(self, mock_validate, mock_run, tmp_path: Path, monkeypatch):
        """Test 'weft logs --tail N' limits lines."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        mock_validate.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(logs, ["meta", "--tail", "50"])

        assert result.exit_code == 0

        call_args = mock_run.call_args[0][0]
        assert "--tail" in call_args
        assert "50" in call_args

    @patch("weft.cli.runtime.logs.validate_docker")
    def test_logs_docker_not_installed(self, mock_validate, tmp_path: Path, monkeypatch):
        """Test 'weft logs' when docker not installed."""
        monkeypatch.chdir(tmp_path)
        mock_validate.return_value = False

        runner = CliRunner()
        result = runner.invoke(logs, ["meta"])

        assert result.exit_code != 0
        assert "Docker is not installed" in result.output


class TestRuntimeIntegration:
    """Integration tests for runtime commands."""

    @patch("subprocess.run")
    @patch("weft.cli.runtime.helpers.validate_docker")
    @patch("weft.cli.runtime.helpers.check_docker_daemon")
    @patch("weft.cli.runtime.up.load_weftrc")
    def test_up_down_workflow(
        self,
        mock_load_config,
        mock_check_daemon,
        mock_validate,
        mock_run,
        tmp_path: Path,
        monkeypatch,
    ):
        """Test full up → down workflow."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        mock_config = Mock()
        mock_config.agents.enabled = ["meta"]
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True
        mock_check_daemon.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()

        # Start runtime
        result_up = runner.invoke(up)
        assert result_up.exit_code == 0
        assert "Runtime started successfully" in result_up.output

        # Stop runtime
        result_down = runner.invoke(down)
        assert result_down.exit_code == 0
        assert "Runtime stopped successfully" in result_down.output


class TestProjectRootDiscovery:
    """Tests for running commands from subdirectories."""

    @patch("subprocess.run")
    @patch("weft.cli.runtime.helpers.validate_docker")
    @patch("weft.cli.runtime.helpers.check_docker_daemon")
    @patch("weft.cli.runtime.up.load_weftrc")
    def test_up_from_subdirectory(
        self,
        mock_load_config,
        mock_check_daemon,
        mock_validate,
        mock_run,
        tmp_path: Path,
        monkeypatch,
    ):
        """Test 'weft up' works from subdirectory."""
        # Setup project root
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\nservices:\n  test: {}\n")

        # Create subdirectory and change to it
        subdir = tmp_path / "src"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        # Mock config
        mock_config = Mock()
        mock_config.agents.enabled = ["meta"]
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True
        mock_check_daemon.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(up)

        assert result.exit_code == 0
        assert "Starting Weft runtime" in result.output
        assert "Runtime started successfully" in result.output

        # Verify docker compose was called with correct path
        call_args = mock_run.call_args[0][0]
        assert "-f" in call_args
        # Path should point to project root, not subdirectory
        compose_idx = call_args.index("-f") + 1
        compose_path = call_args[compose_idx]
        assert compose_path.endswith("docker-compose.yml")
        # Path will contain src since weft is installed there

    @patch("subprocess.run")
    @patch("weft.cli.runtime.helpers.validate_docker")
    @patch("weft.cli.runtime.helpers.check_docker_daemon")
    @patch("weft.cli.runtime.up.load_weftrc")
    def test_up_from_nested_subdirectory(
        self,
        mock_load_config,
        mock_check_daemon,
        mock_validate,
        mock_run,
        tmp_path: Path,
        monkeypatch,
    ):
        """Test 'weft up' works from deeply nested subdirectory."""
        # Setup project root
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        # Create nested subdirectory
        deep_dir = tmp_path / "src" / "deep" / "nested"
        deep_dir.mkdir(parents=True)
        monkeypatch.chdir(deep_dir)

        # Mock config
        mock_config = Mock()
        mock_config.agents.enabled = ["meta"]
        mock_load_config.return_value = mock_config
        mock_validate.return_value = True
        mock_check_daemon.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(up)

        assert result.exit_code == 0
        assert "Runtime started successfully" in result.output

    @patch("weft.cli.runtime.up.validate_docker")
    @patch("weft.cli.runtime.up.check_docker_daemon")
    @patch("weft.cli.runtime.up.load_weftrc")
    def test_up_outside_project(
        self,
        mock_load_config,
        mock_check_daemon,
        mock_validate,
        tmp_path: Path,
        monkeypatch,
    ):
        """Test 'weft up' fails with clear error outside project."""
        # Change to directory without .weftrc.yaml
        monkeypatch.chdir(tmp_path)

        mock_validate.return_value = True
        mock_check_daemon.return_value = True
        mock_load_config.return_value = None  # No config found

        runner = CliRunner()
        result = runner.invoke(up)

        assert result.exit_code != 0
        assert ".weftrc.yaml not found" in result.output

    @patch("subprocess.run")
    @patch("weft.cli.runtime.helpers.validate_docker")
    def test_down_from_subdirectory(
        self,
        mock_validate,
        mock_run,
        tmp_path: Path,
        monkeypatch,
    ):
        """Test 'weft down' works from subdirectory."""
        # Setup project root
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        # Create subdirectory and change to it
        subdir = tmp_path / "src"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        mock_validate.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(down)

        assert result.exit_code == 0
        assert "Runtime stopped successfully" in result.output

        # Verify docker compose was called with correct path
        call_args = mock_run.call_args[0][0]
        assert "-f" in call_args
        compose_idx = call_args.index("-f") + 1
        compose_path = call_args[compose_idx]
        assert compose_path.endswith("docker-compose.yml")

    @patch("subprocess.run")
    @patch("weft.cli.runtime.helpers.validate_docker")
    def test_logs_from_subdirectory(
        self,
        mock_validate,
        mock_run,
        tmp_path: Path,
        monkeypatch,
    ):
        """Test 'weft logs' works from subdirectory."""
        # Setup project root
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n")

        # Create subdirectory and change to it
        subdir = tmp_path / "src"
        subdir.mkdir()
        monkeypatch.chdir(subdir)

        mock_validate.return_value = True
        mock_run.return_value = Mock(returncode=0)

        runner = CliRunner()
        result = runner.invoke(logs, ["meta"])

        assert result.exit_code == 0
        assert "Logs for watcher-meta" in result.output

        # Verify docker compose was called with correct path
        call_args = mock_run.call_args[0][0]
        assert "-f" in call_args


class TestDockerComposeTemplate:
    """Tests for docker-compose.yml template validation."""

    def test_template_includes_agent_id_for_all_services(self):
        """Test that docker-compose template has AGENT_ID set for all watcher services."""
        # Read the docker-compose template
        template_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "src"
            / "weft"
            / "templates"
            / "docker-compose.yml"
        )
        assert template_path.exists(), f"Template not found at {template_path}"

        with open(template_path) as f:
            compose_config = yaml.safe_load(f)

        # Expected agents and their AGENT_ID values
        expected_agents = {
            "watcher-meta": "meta",
            "watcher-architect": "architect",
            "watcher-openapi": "openapi",
            "watcher-ui": "ui",
            "watcher-integration": "integration",
            "watcher-test": "test",
        }

        # Verify each service has AGENT_ID environment variable
        for service_name, expected_agent_id in expected_agents.items():
            assert (
                service_name in compose_config["services"]
            ), f"Service {service_name} not found in template"

            service = compose_config["services"][service_name]
            assert "environment" in service, f"Service {service_name} missing environment section"

            env_list = service["environment"]
            assert isinstance(
                env_list, list
            ), f"Service {service_name} environment should be a list"

            # Check if AGENT_ID is in the environment list
            agent_id_found = False
            for env_var in env_list:
                if isinstance(env_var, str) and env_var.startswith("AGENT_ID="):
                    agent_id_value = env_var.split("=", 1)[1]
                    assert agent_id_value == expected_agent_id, (
                        f"Service {service_name} has AGENT_ID={agent_id_value}, "
                        f"expected AGENT_ID={expected_agent_id}"
                    )
                    agent_id_found = True
                    break

            assert agent_id_found, f"Service {service_name} missing AGENT_ID environment variable"
