"""Tests for CLI utility functions."""

from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from weft.cli.utils import (
    confirm_action,
    echo_error,
    echo_info,
    echo_section_end,
    echo_section_start,
    echo_separator,
    echo_success,
    echo_warning,
    format_path,
    format_timestamp,
)


class TestFormatTimestamp:
    """Tests for format_timestamp function."""

    def test_format_timestamp(self):
        """Test timestamp formatting with default format."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_timestamp(dt)
        assert result == "2024-01-15 10:30:00"

    def test_format_timestamp_none(self):
        """Test formatting None timestamp."""
        result = format_timestamp(None)
        assert result == "Never"

    def test_format_timestamp_custom_format(self):
        """Test timestamp with custom format."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_timestamp(dt, "%Y-%m-%d")
        assert result == "2024-01-15"

    def test_format_timestamp_with_seconds(self):
        """Test timestamp includes seconds."""
        dt = datetime(2024, 1, 15, 10, 30, 45)
        result = format_timestamp(dt)
        assert result == "2024-01-15 10:30:45"

    def test_format_timestamp_iso_format(self):
        """Test timestamp with ISO format."""
        dt = datetime(2024, 1, 15, 10, 30, 0)
        result = format_timestamp(dt, "%Y-%m-%dT%H:%M:%S")
        assert result == "2024-01-15T10:30:00"


class TestFormatPath:
    """Tests for format_path function."""

    def test_format_path_absolute(self):
        """Test formatting absolute path."""
        path = Path("/home/user/code/myapp")
        result = format_path(path)
        assert result == "/home/user/code/myapp"

    def test_format_path_relative(self):
        """Test relative path formatting."""
        path = Path("/home/user/code/myapp")
        base = Path("/home/user")
        result = format_path(path, relative_to=base)
        assert result == "code/myapp"

    def test_format_path_not_relative(self):
        """Test path formatting when not relative."""
        path = Path("/home/user/code/myapp")
        base = Path("/other/path")
        result = format_path(path, relative_to=base)
        assert result == "/home/user/code/myapp"

    def test_format_path_same_path(self):
        """Test formatting when path equals base."""
        path = Path("/home/user")
        base = Path("/home/user")
        result = format_path(path, relative_to=base)
        assert result == "."

    def test_format_path_child_path(self):
        """Test formatting child path."""
        path = Path("/home/user/code/myapp/src")
        base = Path("/home/user/code")
        result = format_path(path, relative_to=base)
        assert result == "myapp/src"


class TestConfirmAction:
    """Tests for confirm_action function."""

    def test_confirm_action_function_exists(self):
        """Test confirm_action function exists and is callable."""
        assert callable(confirm_action)
        # Actual testing would require Click context which is complex
        # The function is a thin wrapper around click.confirm


class TestEchoFunctions:
    """Tests for echo functions."""

    def test_echo_functions_exist(self):
        """Test echo functions exist and are callable."""
        assert callable(echo_success)
        assert callable(echo_error)
        assert callable(echo_warning)
        assert callable(echo_info)

    def test_echo_success_with_click_command(self):
        """Test success message in a Click command."""
        import click

        @click.command()
        def test_cmd():
            echo_success("Test success")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "✓" in result.output
        assert "Test success" in result.output

    def test_echo_error_with_click_command(self):
        """Test error message in a Click command."""
        import click

        @click.command()
        def test_cmd():
            echo_error("Test error")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "✗" in result.output
        assert "Test error" in result.output

    def test_echo_warning_with_click_command(self):
        """Test warning message in a Click command."""
        import click

        @click.command()
        def test_cmd():
            echo_warning("Test warning")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "⚠" in result.output
        assert "Test warning" in result.output

    def test_echo_info_with_click_command(self):
        """Test info message in a Click command."""
        import click

        @click.command()
        def test_cmd():
            echo_info("Test info")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "ℹ" in result.output
        assert "Test info" in result.output


class TestSeparatorFunctions:
    """Tests for separator functions."""

    def test_echo_separator_default(self):
        """Test separator with default width."""
        import click

        @click.command()
        def test_cmd():
            echo_separator()

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "=" * 70 in result.output

    def test_echo_separator_custom_width(self):
        """Test separator with custom width."""
        import click

        @click.command()
        def test_cmd():
            echo_separator(width=50)

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "=" * 50 in result.output

    def test_echo_separator_custom_char(self):
        """Test separator with custom character."""
        import click

        @click.command()
        def test_cmd():
            echo_separator(char="-")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "-" * 70 in result.output

    def test_echo_section_start(self):
        """Test section start with title."""
        import click

        @click.command()
        def test_cmd():
            echo_section_start("TEST SECTION")

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "=" * 70 in result.output
        assert "TEST SECTION" in result.output
        assert result.output.count("=" * 70) == 2

    def test_echo_section_start_custom_width(self):
        """Test section start with custom width."""
        import click

        @click.command()
        def test_cmd():
            echo_section_start("TEST", width=40)

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "=" * 40 in result.output
        assert "TEST" in result.output

    def test_echo_section_end(self):
        """Test section end."""
        import click

        @click.command()
        def test_cmd():
            echo_section_end()

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "=" * 70 in result.output

    def test_echo_section_end_custom_width(self):
        """Test section end with custom width."""
        import click

        @click.command()
        def test_cmd():
            echo_section_end(width=60)

        runner = CliRunner()
        result = runner.invoke(test_cmd)
        assert "=" * 60 in result.output
