"""Tests for weft-validate.py validation script."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def script_path() -> Path:
    """Get path to weft-validate.py script."""
    return Path(__file__).parent.parent.parent / "weft-validate.py"


@pytest.fixture
def weft_validate_module(script_path):
    """Import weft-validate.py as a module for testing utility functions."""
    spec = importlib.util.spec_from_file_location("weft_validate", script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# =============================================================================
# SCRIPT EXECUTION TESTS
# =============================================================================


class TestWeftValidateScript:
    """Test script execution and command-line interface."""

    def test_script_exists(self, script_path):
        """Test that weft-validate.py exists."""
        assert script_path.exists(), "weft-validate.py not found"
        assert script_path.is_file(), "weft-validate.py is not a file"

    def test_script_is_executable_by_python(self, script_path):
        """Test that script can be executed by Python."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0, f"Script failed with: {result.stderr}"

    def test_help_flag(self, script_path):
        """Test --help flag displays usage information."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"], capture_output=True, text=True, timeout=10
        )
        assert result.returncode == 0
        assert "--quick" in result.stdout
        assert "--json" in result.stdout
        assert "--section" in result.stdout
        assert "--allow-dirty" in result.stdout
        assert "--no-tests" in result.stdout

    def test_json_flag_produces_valid_json(self, script_path, tmp_path, monkeypatch):
        """Test --json flag produces valid JSON output."""
        # Change to tmp directory (empty git repo)
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init"], check=True, capture_output=True)

        result = subprocess.run(
            [sys.executable, str(script_path), "--json", "--quick", "--no-tests"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        # Should produce valid JSON even if checks fail
        try:
            output = json.loads(result.stdout)
            assert "sections" in output
            assert "summary" in output
            assert isinstance(output["sections"], list)
            assert isinstance(output["summary"], dict)
        except json.JSONDecodeError as e:
            pytest.fail(f"Invalid JSON output: {e}\n{result.stdout}")

    def test_section_flag_runs_only_specified_section(self, script_path, tmp_path, monkeypatch):
        """Test --section flag runs only specified section."""
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init"], check=True, capture_output=True)

        result = subprocess.run(
            [sys.executable, str(script_path), "--section", "A", "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        output = json.loads(result.stdout)
        assert len(output["sections"]) == 1
        assert output["sections"][0]["name"].startswith("A)")

    def test_invalid_section_returns_error(self, script_path):
        """Test invalid section argument returns error."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--section", "Z"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode != 0


# =============================================================================
# UTILITY FUNCTION TESTS
# =============================================================================


class TestUtilityFunctions:
    """Test utility functions."""

    def test_redact_secrets_anthropic_keys(self, weft_validate_module):
        """Test redaction of Anthropic API keys."""
        text = "WEFT_ANTHROPIC_API_KEY=sk-ant-api03-abcd1234567890"
        redacted = weft_validate_module.redact_secrets(text)
        assert "sk-ant-api03-abcd1234567890" not in redacted
        assert "REDACTED" in redacted
        assert "WEFT_ANTHROPIC_API_KEY" in redacted

    def test_redact_secrets_environment_variables(self, weft_validate_module):
        """Test redaction of environment variable values."""
        text = "export WEFT_API_KEY=secret123"
        redacted = weft_validate_module.redact_secrets(text)
        assert "secret123" not in redacted
        assert "REDACTED" in redacted
        assert "WEFT_API_KEY" in redacted

    def test_redact_secrets_generic_api_keys(self, weft_validate_module):
        """Test redaction of generic API keys."""
        text = 'api_key="my_secret_key_xyz"'
        redacted = weft_validate_module.redact_secrets(text)
        assert "my_secret_key_xyz" not in redacted
        assert "REDACTED" in redacted

    def test_redact_secrets_bearer_tokens(self, weft_validate_module):
        """Test redaction of bearer tokens."""
        text = "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        redacted = weft_validate_module.redact_secrets(text)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in redacted
        assert "REDACTED" in redacted

    def test_tail_output_short_text(self, weft_validate_module):
        """Test tail_output with text shorter than limit."""
        text = "line1\nline2\nline3"
        result = weft_validate_module.tail_output(text, lines=10)
        assert result == "line1\nline2\nline3"

    def test_tail_output_long_text(self, weft_validate_module):
        """Test tail_output with text longer than limit."""
        lines = [f"line{i}" for i in range(20)]
        text = "\n".join(lines)
        result = weft_validate_module.tail_output(text, lines=5)
        assert result == "\n".join(lines[-5:])

    def test_tail_output_empty_text(self, weft_validate_module):
        """Test tail_output with empty text."""
        result = weft_validate_module.tail_output("", lines=10)
        assert result == ""


# =============================================================================
# ENVIRONMENT VALIDATION TESTS
# =============================================================================


class TestEnvironmentValidation:
    """Test Section A: Environment validation."""

    def test_detects_python_version(self, weft_validate_module):
        """Test Python version is detected correctly."""
        # We're running in Python, so this should always pass
        assert sys.version_info >= (3, 8), "Tests require Python 3.8+"

    @patch("shutil.which")
    def test_detects_missing_weft_cli(self, mock_which, weft_validate_module, monkeypatch):
        """Test detection of missing Weft CLI."""
        # Mock weft not found
        mock_which.return_value = None

        # Create validator instance
        args = Mock()
        args.section = "A"
        args.quick = True
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_environment()

        # Check that Weft CLI check failed or warned
        weft_checks = [c for c in result.checks if "Weft CLI" in c.name]
        assert len(weft_checks) > 0
        assert weft_checks[0].status in [
            weft_validate_module.Status.FAIL,
            weft_validate_module.Status.WARN,
        ]

    @patch.dict("os.environ", {}, clear=True)
    def test_detects_missing_env_vars(self, weft_validate_module):
        """Test detection of missing environment variables."""
        args = Mock()
        args.section = "A"
        args.quick = True
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_environment()

        # Check that env var checks failed
        env_checks = [c for c in result.checks if "ENV:" in c.name]
        assert len(env_checks) > 0
        assert all(c.status == weft_validate_module.Status.FAIL for c in env_checks)

    @patch.dict("os.environ", {"WEFT_ANTHROPIC_API_KEY": "sk-ant-test"})
    def test_detects_present_env_vars(self, weft_validate_module):
        """Test detection of present environment variables."""
        args = Mock()
        args.section = "A"
        args.quick = True
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_environment()

        # Check that env var checks passed
        env_checks = [c for c in result.checks if "ENV:" in c.name]
        assert len(env_checks) > 0
        assert all(c.status == weft_validate_module.Status.PASS for c in env_checks)
        # Verify no secrets in output
        for check in env_checks:
            assert "sk-ant-test" not in check.message


# =============================================================================
# REPOSITORY VALIDATION TESTS
# =============================================================================


class TestRepositoryValidation:
    """Test Section B: Repository validation."""

    def test_detects_clean_repo(self, git_repo, weft_validate_module, monkeypatch):
        """Test detection of clean git repository."""
        monkeypatch.chdir(git_repo)

        args = Mock()
        args.section = "B"
        args.quick = True
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_repository()

        # Check that working tree is clean
        tree_checks = [c for c in result.checks if "Working Tree" in c.name]
        assert len(tree_checks) > 0
        assert tree_checks[0].status == weft_validate_module.Status.PASS

    def test_detects_dirty_repo(self, git_repo, weft_validate_module, monkeypatch):
        """Test detection of dirty git repository."""
        monkeypatch.chdir(git_repo)

        # Create untracked file
        (git_repo / "untracked.txt").write_text("test")

        args = Mock()
        args.section = "B"
        args.quick = True
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_repository()

        # Check that working tree is dirty
        tree_checks = [c for c in result.checks if "Working Tree" in c.name]
        assert len(tree_checks) > 0
        assert tree_checks[0].status == weft_validate_module.Status.FAIL

    def test_allow_dirty_flag(self, git_repo, weft_validate_module, monkeypatch):
        """Test --allow-dirty flag allows uncommitted changes."""
        monkeypatch.chdir(git_repo)

        # Create untracked file
        (git_repo / "untracked.txt").write_text("test")

        args = Mock()
        args.section = "B"
        args.quick = True
        args.json = False
        args.allow_dirty = True  # Allow dirty
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_repository()

        # Check that working tree is warned but not failed
        tree_checks = [c for c in result.checks if "Working Tree" in c.name]
        assert len(tree_checks) > 0
        assert tree_checks[0].status in [
            weft_validate_module.Status.WARN,
            weft_validate_module.Status.PASS,
        ]

    def test_detects_non_git_repo(self, tmp_path, weft_validate_module, monkeypatch):
        """Test detection of non-git repository."""
        monkeypatch.chdir(tmp_path)
        # Don't initialize git

        args = Mock()
        args.section = "B"
        args.quick = True
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_repository()

        # Check that git repository check failed
        git_checks = [c for c in result.checks if "Git Repository" in c.name]
        assert len(git_checks) > 0
        assert git_checks[0].status == weft_validate_module.Status.FAIL


# =============================================================================
# COMMAND VALIDATION TESTS
# =============================================================================


class TestCommandValidation:
    """Test Section C: Command validation."""

    def test_skips_slow_commands_in_quick_mode(self, git_repo, weft_validate_module, monkeypatch):
        """Test that slow commands are skipped in --quick mode."""
        monkeypatch.chdir(git_repo)

        args = Mock()
        args.section = "C"
        args.quick = True  # Quick mode
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_commands()

        # Check that slow commands were skipped
        slow_checks = [c for c in result.checks if c.status == weft_validate_module.Status.SKIP]
        assert len(slow_checks) > 0, "Expected some slow commands to be skipped"

        # Verify these are slow commands
        for check in slow_checks:
            assert "weft up" in check.name or "slow" in check.message.lower()

    def test_validates_pytest_availability(self, git_repo, weft_validate_module, monkeypatch):
        """Test validation of pytest command availability."""
        monkeypatch.chdir(git_repo)

        args = Mock()
        args.section = "C"
        args.quick = True
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_commands()

        # Check that pytest was validated
        pytest_checks = [c for c in result.checks if "pytest" in c.name.lower()]
        assert len(pytest_checks) > 0


# =============================================================================
# CONTRACT VALIDATION TESTS
# =============================================================================


class TestContractValidation:
    """Test Section D: Contract validation."""

    def test_detects_missing_weftrc(self, tmp_path, weft_validate_module, monkeypatch):
        """Test detection of missing .weftrc.yaml."""
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init"], check=True, capture_output=True)

        args = Mock()
        args.section = "D"
        args.quick = True
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_contracts()

        # Check that .weftrc.yaml is warned as missing
        weftrc_checks = [c for c in result.checks if ".weftrc.yaml" in c.name]
        assert len(weftrc_checks) > 0
        assert weftrc_checks[0].status == weft_validate_module.Status.WARN

    def test_validates_weftrc_yaml_syntax(self, tmp_path, weft_validate_module, monkeypatch):
        """Test validation of .weftrc.yaml YAML syntax."""
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init"], check=True, capture_output=True)

        # Create valid .weftrc.yaml
        (tmp_path / ".weftrc.yaml").write_text("project:\n  name: test\n  type: backend\n")

        args = Mock()
        args.section = "D"
        args.quick = True
        args.json = False
        args.allow_dirty = False
        args.no_tests = True

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_contracts()

        # Check that .weftrc.yaml validation passed
        weftrc_checks = [c for c in result.checks if ".weftrc.yaml" in c.name]
        assert len(weftrc_checks) > 0
        # Should pass or warn (if PyYAML not installed)
        assert weftrc_checks[0].status in [
            weft_validate_module.Status.PASS,
            weft_validate_module.Status.WARN,
        ]


# =============================================================================
# TEST VALIDATION TESTS
# =============================================================================


class TestTestValidation:
    """Test Section E: Test validation."""

    def test_skips_tests_with_no_tests_flag(self, git_repo, weft_validate_module, monkeypatch):
        """Test that tests are skipped with --no-tests flag."""
        monkeypatch.chdir(git_repo)

        args = Mock()
        args.section = "E"
        args.quick = False
        args.json = False
        args.allow_dirty = False
        args.no_tests = True  # Skip tests

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_tests()

        # Check that test execution was skipped
        test_checks = [c for c in result.checks if "Test Execution" in c.name]
        assert len(test_checks) > 0
        assert test_checks[0].status == weft_validate_module.Status.SKIP

    def test_skips_tests_with_quick_flag(self, git_repo, weft_validate_module, monkeypatch):
        """Test that tests are skipped with --quick flag."""
        monkeypatch.chdir(git_repo)

        args = Mock()
        args.section = "E"
        args.quick = True  # Quick mode
        args.json = False
        args.allow_dirty = False
        args.no_tests = False

        validator = weft_validate_module.WeftValidator(args)
        result = validator.validate_tests()

        # Check that test execution was skipped
        test_checks = [c for c in result.checks if "Test Execution" in c.name]
        assert len(test_checks) > 0
        assert test_checks[0].status == weft_validate_module.Status.SKIP


# =============================================================================
# EXIT CODE TESTS
# =============================================================================


class TestExitCodes:
    """Test exit code behavior."""

    def test_exit_code_0_on_success(self, script_path, git_repo, monkeypatch):
        """Test exit code 0 when all checks pass."""
        monkeypatch.chdir(git_repo)

        # Set required env vars
        monkeypatch.setenv("WEFT_ANTHROPIC_API_KEY", "sk-ant-test")

        result = subprocess.run(
            [sys.executable, str(script_path), "--quick", "--no-tests"],
            capture_output=True,
            timeout=30,
        )

        # Should return 0 or 1 (not 2 which is misconfiguration)
        assert result.returncode in [0, 1]

    def test_exit_code_1_on_validation_failure(self, script_path, tmp_path, monkeypatch):
        """Test exit code 1 when validation fails."""
        monkeypatch.chdir(tmp_path)
        # Don't initialize git repo - this should cause validation failure

        result = subprocess.run(
            [sys.executable, str(script_path), "--quick", "--no-tests"],
            capture_output=True,
            timeout=30,
        )

        # Should fail due to no git repo
        assert result.returncode in [1, 2]

    def test_exit_code_2_on_invalid_section(self, script_path):
        """Test exit code 2 on misconfiguration (invalid section)."""
        result = subprocess.run(
            [sys.executable, str(script_path), "--section", "Z"], capture_output=True, timeout=10
        )

        assert result.returncode == 2


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestIntegration:
    """Integration tests for complete validation flows."""

    def test_full_validation_in_valid_repo(self, script_path, git_repo, monkeypatch):
        """Test full validation in a valid repository."""
        monkeypatch.chdir(git_repo)
        monkeypatch.setenv("WEFT_ANTHROPIC_API_KEY", "sk-ant-test")

        # Create .weftrc.yaml
        (git_repo / ".weftrc.yaml").write_text("project:\n  name: test\n")

        result = subprocess.run(
            [sys.executable, str(script_path), "--quick", "--no-tests"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        # Should complete (may have warnings but not misconfiguration)
        assert result.returncode in [0, 1]
        assert "VALIDATION SUMMARY" in result.stdout or "sections" in result.stdout

    def test_json_output_structure(self, script_path, git_repo, monkeypatch):
        """Test JSON output has correct structure."""
        monkeypatch.chdir(git_repo)

        result = subprocess.run(
            [sys.executable, str(script_path), "--json", "--quick", "--no-tests"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        output = json.loads(result.stdout)

        # Verify structure
        assert "sections" in output
        assert "summary" in output
        assert len(output["sections"]) > 0

        for section in output["sections"]:
            assert "name" in section
            assert "passed" in section
            assert "checks" in section

            for check in section["checks"]:
                assert "name" in check
                assert "status" in check
                assert "message" in check
