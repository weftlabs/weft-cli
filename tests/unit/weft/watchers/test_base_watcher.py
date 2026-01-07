"""Tests for BaseWatcher class."""

import signal
import threading
import time
from pathlib import Path

import pytest

from weft.queue.file_ops import write_prompt
from weft.queue.models import PromptTask
from weft.watchers.base import BaseWatcher


class TestWatcher(BaseWatcher):
    """Test implementation of BaseWatcher for testing."""

    def __init__(self, *args, **kwargs):
        self.processed_prompts = []
        super().__init__(*args, **kwargs)

    def process_prompt(self, prompt_task: PromptTask) -> str:
        """Test implementation that records processed prompts."""
        self.processed_prompts.append(prompt_task)
        return f"Processed: {prompt_task.prompt_text}"


class ErrorWatcher(BaseWatcher):
    """Test watcher that raises errors."""

    def process_prompt(self, prompt_task: PromptTask) -> str:
        """Always raises an error."""
        raise ValueError("Test error during processing")


class TestBaseWatcherInitialization:
    """Tests for BaseWatcher initialization."""

    def test_initialization_basic(self, temp_dir: Path) -> None:
        """Test basic watcher initialization."""
        watcher = TestWatcher("feat/test", "01-architect", temp_dir)

        assert watcher.feature_id == "feat/test"
        assert watcher.agent_id == "01-architect"
        assert watcher.ai_history_path == temp_dir
        assert watcher.poll_interval == 2  # Default

    def test_initialization_custom_poll_interval(self, temp_dir: Path) -> None:
        """Test initialization with custom poll interval."""
        watcher = TestWatcher("feat/test", "01-architect", temp_dir, poll_interval=5)

        assert watcher.poll_interval == 5

    def test_agent_dir_path(self, temp_dir: Path) -> None:
        """Test that agent_dir is set correctly."""
        watcher = TestWatcher("feat/test", "01-architect", temp_dir)

        expected = temp_dir / "feat/test" / "01-architect"
        assert watcher.agent_dir == expected

    def test_is_running_initially_false(self, temp_dir: Path) -> None:
        """Test that is_running is False initially."""
        watcher = TestWatcher("feat/test", "01-architect", temp_dir)

        assert not watcher.is_running


class TestAbstractMethod:
    """Tests for abstract process_prompt method."""

    def test_cannot_instantiate_base_class(self, temp_dir: Path) -> None:
        """Test that BaseWatcher cannot be instantiated directly."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseWatcher("feat/test", "01-architect", temp_dir)

    def test_must_implement_process_prompt(self, temp_dir: Path) -> None:
        """Test that subclasses must implement process_prompt."""

        class IncompleteWatcher(BaseWatcher):
            pass

        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            IncompleteWatcher("feat/test", "01-architect", temp_dir)


class TestStartStop:
    """Tests for start/stop methods."""

    def test_start_sets_running_flag(self, temp_dir: Path) -> None:
        """Test that start() sets the running flag."""
        watcher = TestWatcher("feat/test", "01-architect", temp_dir)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        # Wait for watcher to start
        time.sleep(0.1)

        assert watcher.is_running

        watcher.stop()
        thread.join(timeout=2)

    def test_stop_clears_running_flag(self, temp_dir: Path) -> None:
        """Test that stop() clears the running flag."""
        watcher = TestWatcher("feat/test", "01-architect", temp_dir)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        time.sleep(0.1)
        watcher.stop()
        thread.join(timeout=2)

        assert not watcher.is_running

    def test_watcher_exits_after_stop(self, temp_dir: Path) -> None:
        """Test that watcher exits gracefully after stop()."""
        watcher = TestWatcher("feat/test", "01-architect", temp_dir)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        time.sleep(0.1)
        watcher.stop()
        thread.join(timeout=2)

        # Thread should complete
        assert not thread.is_alive()


class TestPromptProcessing:
    """Tests for prompt processing."""

    def test_processes_single_prompt(self, temp_dir: Path) -> None:
        """Test processing a single prompt."""
        # Create directories
        agent_dir = temp_dir / "feat/test" / "01-architect"
        (agent_dir / "in").mkdir(parents=True)
        (agent_dir / "out").mkdir(parents=True)

        # Write a prompt
        prompt = PromptTask("feat/test", "01-architect", "Design a system")
        prompt_file = write_prompt(temp_dir, "feat/test", "01-architect", prompt)

        # Create watcher and process
        watcher = TestWatcher("feat/test", "01-architect", temp_dir, poll_interval=1)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        # Wait for processing
        time.sleep(2)
        watcher.stop()
        thread.join(timeout=2)

        # Verify prompt was processed
        assert len(watcher.processed_prompts) == 1
        assert watcher.processed_prompts[0].prompt_text == "Design a system"

        # Verify file was marked as processed
        assert not prompt_file.exists()
        processed_file = prompt_file.with_suffix(".processed")
        assert processed_file.exists()

        # Verify result was written
        results = list((agent_dir / "out").glob("*_result.md"))
        assert len(results) == 1
        result_content = results[0].read_text()
        assert "Processed: Design a system" in result_content
        assert "feature: feat/test" in result_content
        assert "agent: 01-architect" in result_content

    def test_processes_multiple_prompts(self, temp_dir: Path) -> None:
        """Test processing multiple prompts."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        (agent_dir / "in").mkdir(parents=True)
        (agent_dir / "out").mkdir(parents=True)

        # Write multiple prompts
        prompts = [
            PromptTask("feat/test", "01-architect", "First prompt"),
            PromptTask("feat/test", "01-architect", "Second prompt"),
            PromptTask("feat/test", "01-architect", "Third prompt"),
        ]

        for prompt in prompts:
            write_prompt(temp_dir, "feat/test", "01-architect", prompt)
            time.sleep(0.01)  # Ensure different timestamps

        # Process prompts
        watcher = TestWatcher("feat/test", "01-architect", temp_dir, poll_interval=1)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        # Wait for all to process
        time.sleep(3)
        watcher.stop()
        thread.join(timeout=2)

        # Verify all were processed
        assert len(watcher.processed_prompts) == 3

        # Verify all results written
        results = list((agent_dir / "out").glob("*_result.md"))
        assert len(results) == 3

        # Verify no pending prompts remain
        pending = list((agent_dir / "in").glob("*.md"))
        assert len(pending) == 0

    def test_processes_prompts_in_order(self, temp_dir: Path) -> None:
        """Test that prompts are processed in FIFO order."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        (agent_dir / "in").mkdir(parents=True)
        (agent_dir / "out").mkdir(parents=True)

        # Write prompts with delays
        for i in range(3):
            prompt = PromptTask("feat/test", "01-architect", f"Prompt {i}")
            write_prompt(temp_dir, "feat/test", "01-architect", prompt)
            time.sleep(0.01)

        watcher = TestWatcher("feat/test", "01-architect", temp_dir, poll_interval=1)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        time.sleep(3)
        watcher.stop()
        thread.join(timeout=2)

        # Verify order
        assert watcher.processed_prompts[0].prompt_text == "Prompt 0"
        assert watcher.processed_prompts[1].prompt_text == "Prompt 1"
        assert watcher.processed_prompts[2].prompt_text == "Prompt 2"

    def test_no_prompts_does_not_error(self, temp_dir: Path) -> None:
        """Test that watcher handles no prompts gracefully."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        (agent_dir / "in").mkdir(parents=True)
        (agent_dir / "out").mkdir(parents=True)

        watcher = TestWatcher("feat/test", "01-architect", temp_dir, poll_interval=1)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        time.sleep(2)
        watcher.stop()
        thread.join(timeout=2)

        # Should complete without errors
        assert len(watcher.processed_prompts) == 0


class TestErrorHandling:
    """Tests for error handling."""

    def test_handles_processing_error(self, temp_dir: Path) -> None:
        """Test that processing errors are handled gracefully."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        (agent_dir / "in").mkdir(parents=True)
        (agent_dir / "out").mkdir(parents=True)

        # Write a prompt
        prompt = PromptTask("feat/test", "01-architect", "Test prompt")
        prompt_file = write_prompt(temp_dir, "feat/test", "01-architect", prompt)

        # Use watcher that raises errors
        watcher = ErrorWatcher("feat/test", "01-architect", temp_dir, poll_interval=1)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        time.sleep(2)
        watcher.stop()
        thread.join(timeout=2)

        # Prompt should be marked as processed even with error
        assert not prompt_file.exists()
        processed_file = prompt_file.with_suffix(".processed")
        assert processed_file.exists()

        # Error result should be written
        results = list((agent_dir / "out").glob("*_result.md"))
        assert len(results) == 1
        result_content = results[0].read_text()
        assert "ERROR: Test error during processing" in result_content

    def test_continues_after_error(self, temp_dir: Path) -> None:
        """Test that watcher continues processing after an error."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        (agent_dir / "in").mkdir(parents=True)
        (agent_dir / "out").mkdir(parents=True)

        # Write multiple prompts
        for i in range(3):
            prompt = PromptTask("feat/test", "01-architect", f"Prompt {i}")
            write_prompt(temp_dir, "feat/test", "01-architect", prompt)
            time.sleep(0.01)

        # Use error watcher
        watcher = ErrorWatcher("feat/test", "01-architect", temp_dir, poll_interval=1)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        time.sleep(3)
        watcher.stop()
        thread.join(timeout=2)

        # All prompts should have error results
        results = list((agent_dir / "out").glob("*_result.md"))
        assert len(results) == 3

        # No pending prompts
        pending = list((agent_dir / "in").glob("*.md"))
        assert len(pending) == 0


class TestSignalHandling:
    """Tests for signal handling."""

    def test_signal_handler_stops_watcher(self, temp_dir: Path) -> None:
        """Test that signal handler stops the watcher."""
        watcher = TestWatcher("feat/test", "01-architect", temp_dir)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        time.sleep(0.1)

        # Send signal
        watcher._signal_handler(signal.SIGINT, None)

        thread.join(timeout=2)

        assert not watcher.is_running
        assert not thread.is_alive()


@pytest.mark.timeout(30)
class TestIntegration:
    """Integration tests for complete workflows."""

    def test_full_workflow_single_prompt(self, temp_dir: Path) -> None:
        """Test complete workflow with single prompt."""
        # Setup
        agent_dir = temp_dir / "feat/workflow" / "01-architect"
        (agent_dir / "in").mkdir(parents=True)
        (agent_dir / "out").mkdir(parents=True)

        # Write prompt
        prompt = PromptTask(
            feature_id="feat/workflow",
            agent_id="01-architect",
            prompt_text="Design a microservices architecture",
            spec_version="1.0.0",
            revision=1,
        )
        prompt_file = write_prompt(temp_dir, "feat/workflow", "01-architect", prompt)

        # Start watcher
        watcher = TestWatcher("feat/workflow", "01-architect", temp_dir, poll_interval=1)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        # Wait for processing
        time.sleep(2)
        watcher.stop()
        thread.join(timeout=2)

        # Verify complete workflow
        # 1. Prompt processed
        assert len(watcher.processed_prompts) == 1

        # 2. Prompt marked as processed
        assert not prompt_file.exists()
        assert prompt_file.with_suffix(".processed").exists()

        # 3. Result written
        results = list((agent_dir / "out").glob("*_result.md"))
        assert len(results) == 1

        # 4. Result has audit frontmatter
        result_content = results[0].read_text()
        assert "feature: feat/workflow" in result_content
        assert "agent: 01-architect" in result_content
        assert "prompt_hash:" in result_content
        assert "output_hash:" in result_content
        assert "generated_at:" in result_content
        assert "Processed: Design a microservices architecture" in result_content

    def test_mixed_success_and_error_prompts(self, temp_dir: Path) -> None:
        """Test handling mix of successful and error prompts."""

        class MixedWatcher(BaseWatcher):
            def process_prompt(self, prompt_task: PromptTask) -> str:
                if "error" in prompt_task.prompt_text.lower():
                    raise ValueError("Intentional error")
                return f"Success: {prompt_task.prompt_text}"

        agent_dir = temp_dir / "feat/mixed" / "01-architect"
        (agent_dir / "in").mkdir(parents=True)
        (agent_dir / "out").mkdir(parents=True)

        # Write mixed prompts
        prompts = [
            PromptTask("feat/mixed", "01-architect", "Good prompt 1"),
            PromptTask("feat/mixed", "01-architect", "ERROR prompt"),
            PromptTask("feat/mixed", "01-architect", "Good prompt 2"),
        ]

        for prompt in prompts:
            write_prompt(temp_dir, "feat/mixed", "01-architect", prompt)
            time.sleep(0.01)

        watcher = MixedWatcher("feat/mixed", "01-architect", temp_dir, poll_interval=1)

        def run_watcher():
            watcher.start()

        thread = threading.Thread(target=run_watcher, daemon=True)
        thread.start()

        time.sleep(3)
        watcher.stop()
        thread.join(timeout=2)

        # All should have results
        results = list((agent_dir / "out").glob("*_result.md"))
        assert len(results) == 3

        # Check content
        result_texts = [r.read_text() for r in results]
        success_count = sum(1 for r in result_texts if "Success:" in r)
        error_count = sum(1 for r in result_texts if "ERROR:" in r)

        assert success_count == 2
        assert error_count == 1
