"""Tests for agent orchestration utilities."""

import time
from unittest.mock import MagicMock, patch

import pytest

from weft.agents.orchestration import submit_prompt_to_agent, wait_for_agent_result


class TestSubmitPromptToAgent:
    """Tests for submit_prompt_to_agent function."""

    @patch("weft.agents.orchestration.write_prompt")
    def test_submit_with_revision(self, mock_write_prompt, tmp_path):
        """Test submitting prompt with revision number."""
        # Arrange
        feature_id = "test-feature"
        agent_id = "00-meta"
        prompt_content = "Test prompt"
        revision = 2
        expected_file = tmp_path / "test_prompt.md"
        mock_write_prompt.return_value = expected_file

        # Act
        result = submit_prompt_to_agent(
            feature_id=feature_id,
            agent_id=agent_id,
            prompt_content=prompt_content,
            ai_history_path=tmp_path,
            revision=revision,
        )

        # Assert
        assert result == expected_file
        mock_write_prompt.assert_called_once()
        call_args = mock_write_prompt.call_args
        assert call_args.kwargs["ai_history_path"] == tmp_path
        assert call_args.kwargs["feature_id"] == feature_id
        assert call_args.kwargs["agent_id"] == agent_id
        prompt_task = call_args.kwargs["prompt_task"]
        assert prompt_task.feature_id == feature_id
        assert prompt_task.agent_id == agent_id
        assert prompt_task.prompt_text == prompt_content
        assert prompt_task.revision == revision

    @patch("weft.agents.orchestration.write_prompt")
    def test_submit_without_revision(self, mock_write_prompt, tmp_path):
        """Test submitting prompt without revision (timestamp-based naming)."""
        # Arrange
        feature_id = "test-feature"
        agent_id = "01-architect"
        prompt_content = "Another test"
        expected_file = tmp_path / "test_prompt.md"
        mock_write_prompt.return_value = expected_file

        # Act
        result = submit_prompt_to_agent(
            feature_id=feature_id,
            agent_id=agent_id,
            prompt_content=prompt_content,
            ai_history_path=tmp_path,
        )

        # Assert
        assert result == expected_file
        call_args = mock_write_prompt.call_args
        prompt_task = call_args.kwargs["prompt_task"]
        assert prompt_task.revision is None

    @patch("weft.agents.orchestration.write_prompt")
    def test_submit_creates_prompt_task(self, mock_write_prompt, tmp_path):
        """Test that PromptTask is created with correct spec_version."""
        # Arrange
        expected_file = tmp_path / "test.md"
        mock_write_prompt.return_value = expected_file

        # Act
        submit_prompt_to_agent(
            feature_id="feat",
            agent_id="agent",
            prompt_content="content",
            ai_history_path=tmp_path,
        )

        # Assert
        prompt_task = mock_write_prompt.call_args.kwargs["prompt_task"]
        assert prompt_task.spec_version == "1.0.0"


class TestWaitForAgentResult:
    """Tests for wait_for_agent_result function."""

    @pytest.fixture
    def mock_output_dir(self, tmp_path):
        """Create mock output directory structure."""
        feature_dir = tmp_path / "test-feature"
        agent_dir = feature_dir / "00-meta"
        output_dir = agent_dir / "out"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def test_wait_returns_result_when_found(self, mock_output_dir, tmp_path):
        """Test that result is returned when file is found."""
        # Arrange
        result_content = "# Test Result\nSome output"
        result_file = mock_output_dir / "20231215_120000_000000_result.md"
        result_file.write_text(result_content)

        # Act (use min_timestamp=0 to accept pre-existing files)
        result = wait_for_agent_result(
            feature_id="test-feature",
            agent_id="00-meta",
            ai_history_path=tmp_path,
            timeout=5,
            min_timestamp=0,
            show_progress=False,
        )

        # Assert
        assert result == result_content

    def test_wait_returns_none_on_timeout(self, mock_output_dir, tmp_path):
        """Test that None is returned when timeout is reached."""
        # Act
        result = wait_for_agent_result(
            feature_id="test-feature",
            agent_id="00-meta",
            ai_history_path=tmp_path,
            timeout=2,
            show_progress=False,
        )

        # Assert
        assert result is None

    def test_wait_filters_by_timestamp(self, mock_output_dir, tmp_path):
        """Test that only results newer than min_timestamp are returned."""
        # Arrange
        old_result = mock_output_dir / "20231215_100000_000000_result.md"
        old_result.write_text("Old content")
        old_time = time.time() - 100  # 100 seconds ago

        # Set old file's modification time
        import os

        os.utime(old_result, (old_time, old_time))

        # Act with timestamp after old file
        result = wait_for_agent_result(
            feature_id="test-feature",
            agent_id="00-meta",
            ai_history_path=tmp_path,
            timeout=2,
            min_timestamp=time.time() - 50,  # Only accept files from last 50 seconds
            show_progress=False,
        )

        # Assert
        assert result is None  # Old file should be filtered out

    def test_wait_returns_most_recent_result(self, mock_output_dir, tmp_path):
        """Test that the most recent result is returned when multiple exist."""
        # Arrange
        result1 = mock_output_dir / "20231215_100000_000000_result.md"
        result2 = mock_output_dir / "20231215_110000_000000_result.md"
        result1.write_text("First result")
        time.sleep(0.1)  # Ensure different timestamps
        result2.write_text("Second result")

        # Act (use min_timestamp=0 to accept pre-existing files)
        result = wait_for_agent_result(
            feature_id="test-feature",
            agent_id="00-meta",
            ai_history_path=tmp_path,
            timeout=5,
            min_timestamp=0,
            show_progress=False,
        )

        # Assert
        assert result == "Second result"

    def test_wait_creates_output_dir_if_missing(self, tmp_path):
        """Test that output directory is created if it doesn't exist."""
        # Act
        wait_for_agent_result(
            feature_id="new-feature",
            agent_id="01-architect",
            ai_history_path=tmp_path,
            timeout=1,
            show_progress=False,
        )

        # Assert
        output_dir = tmp_path / "new-feature" / "01-architect" / "out"
        assert output_dir.exists()
        assert output_dir.is_dir()

    @patch("weft.agents.orchestration.click.progressbar")
    def test_wait_shows_progress_bar(self, mock_progressbar, mock_output_dir, tmp_path):
        """Test that progress bar is shown when show_progress=True."""
        # Arrange
        mock_bar = MagicMock()
        mock_progressbar.return_value.__enter__.return_value = mock_bar

        # Create result file
        result_file = mock_output_dir / "20231215_120000_000000_result.md"
        result_file.write_text("Content")

        # Act
        wait_for_agent_result(
            feature_id="test-feature",
            agent_id="00-meta",
            ai_history_path=tmp_path,
            timeout=5,
            show_progress=True,
        )

        # Assert
        mock_progressbar.assert_called_once()
        assert "00-meta" in str(mock_progressbar.call_args)

    def test_wait_no_progress_bar_when_disabled(self, mock_output_dir, tmp_path):
        """Test that progress bar is not shown when show_progress=False."""
        # Arrange
        result_file = mock_output_dir / "20231215_120000_000000_result.md"
        result_file.write_text("Content")

        # Act - should not raise any click.progressbar errors
        with patch("weft.agents.orchestration.click.progressbar") as mock_progressbar:
            result = wait_for_agent_result(
                feature_id="test-feature",
                agent_id="00-meta",
                ai_history_path=tmp_path,
                timeout=5,
                min_timestamp=0,  # Accept pre-existing files
                show_progress=False,
            )

            # Assert
            mock_progressbar.assert_not_called()
            assert result is not None

    def test_wait_polls_at_regular_intervals(self, mock_output_dir, tmp_path):
        """Test that wait function polls at regular intervals."""
        # Arrange
        result_file = mock_output_dir / "20231215_120000_000000_result.md"

        # Capture start time before creating thread
        start_time = time.time()

        # Create result file after a delay
        def create_file_after_delay():
            time.sleep(1)
            result_file.write_text("Delayed content")

        import threading

        thread = threading.Thread(target=create_file_after_delay)
        thread.start()

        # Act (use min_timestamp captured before thread starts)
        result = wait_for_agent_result(
            feature_id="test-feature",
            agent_id="00-meta",
            ai_history_path=tmp_path,
            timeout=5,
            min_timestamp=start_time,
            show_progress=False,
        )
        elapsed = time.time() - start_time

        thread.join()

        # Assert
        assert result == "Delayed content"
        assert elapsed >= 1  # Should have waited for file
        assert elapsed < 3  # But not too long
