"""Tests for queue file operations."""

import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from weft.audit.hashing import sha256_hash
from weft.queue.file_ops import (
    list_pending_prompts,
    mark_processed,
    read_prompt,
    write_prompt,
    write_result,
)
from weft.queue.models import PromptTask, ResultTask


class TestWritePrompt:
    """Tests for write_prompt function."""

    def test_write_prompt_creates_file(self, temp_dir: Path) -> None:
        """Test that write_prompt creates a file."""
        prompt = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Design a system",
        )

        path = write_prompt(temp_dir, "feat/test", "01-architect", prompt)

        assert path.exists()
        assert path.is_file()

    def test_write_prompt_creates_directory_structure(self, temp_dir: Path) -> None:
        """Test that write_prompt creates necessary directories."""
        prompt = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Test",
        )

        path = write_prompt(temp_dir, "feat/test", "01-architect", prompt)

        # Verify directory structure
        expected_dir = temp_dir / "feat/test" / "01-architect" / "in"
        assert expected_dir.exists()
        assert path.parent == expected_dir

    def test_write_prompt_filename_format(self, temp_dir: Path) -> None:
        """Test that filename has correct format."""
        prompt = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Test",
        )

        path = write_prompt(temp_dir, "feat/test", "01-architect", prompt)

        # Should end with _prompt.md
        assert path.name.endswith("_prompt.md")
        # Should have timestamp format YYYYMMDD_HHMMSS
        assert len(path.stem.split("_")) >= 3  # date_time_prompt

    def test_write_prompt_content(self, temp_dir: Path) -> None:
        """Test that written file contains correct content."""
        prompt = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Design a user authentication system",
            spec_version="1.2.3",
            revision=5,
        )

        path = write_prompt(temp_dir, "feat/test", "01-architect", prompt)

        content = path.read_text()
        assert "feature: feat/test" in content
        assert "agent: 01-architect" in content
        assert "prompt_spec_version: 1.2.3" in content
        assert "revision: 5" in content
        assert "Design a user authentication system" in content

    def test_write_prompt_multiple_files(self, temp_dir: Path) -> None:
        """Test writing multiple prompts creates separate files."""
        prompt1 = PromptTask("feat/test", "01-architect", "First prompt")
        prompt2 = PromptTask("feat/test", "01-architect", "Second prompt")

        # Add small delay to ensure different timestamps
        path1 = write_prompt(temp_dir, "feat/test", "01-architect", prompt1)
        time.sleep(0.1)
        path2 = write_prompt(temp_dir, "feat/test", "01-architect", prompt2)

        assert path1 != path2
        assert path1.exists()
        assert path2.exists()

    def test_write_prompt_nested_feature_id(self, temp_dir: Path) -> None:
        """Test with nested feature ID."""
        prompt = PromptTask(
            feature_id="epic/feat/sub-feature",
            agent_id="02-openapi",
            prompt_text="Test",
        )

        path = write_prompt(temp_dir, "epic/feat/sub-feature", "02-openapi", prompt)

        assert path.exists()
        assert "epic/feat/sub-feature" in str(path.parent.parent.parent)


class TestReadPrompt:
    """Tests for read_prompt function."""

    def test_read_prompt_success(self, temp_dir: Path) -> None:
        """Test reading a valid prompt file."""
        prompt = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Design a system",
        )

        path = write_prompt(temp_dir, "feat/test", "01-architect", prompt)
        parsed = read_prompt(path)

        assert parsed.feature_id == "feat/test"
        assert parsed.agent_id == "01-architect"
        assert parsed.prompt_text == "Design a system"

    def test_read_prompt_with_custom_values(self, temp_dir: Path) -> None:
        """Test reading prompt with custom spec_version and revision."""
        prompt = PromptTask(
            feature_id="feat/custom",
            agent_id="02-openapi",
            prompt_text="API design",
            spec_version="2.1.0",
            revision=10,
        )

        path = write_prompt(temp_dir, "feat/custom", "02-openapi", prompt)
        parsed = read_prompt(path)

        assert parsed.spec_version == "2.1.0"
        assert parsed.revision == 10

    def test_read_prompt_file_not_found(self, temp_dir: Path) -> None:
        """Test reading non-existent file raises FileNotFoundError."""
        nonexistent = temp_dir / "does-not-exist.md"

        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            read_prompt(nonexistent)

    def test_read_prompt_invalid_format(self, temp_dir: Path) -> None:
        """Test reading invalid file format raises ValueError."""
        invalid_file = temp_dir / "invalid.md"
        invalid_file.write_text("Just some text without frontmatter")

        with pytest.raises(ValueError):
            read_prompt(invalid_file)


class TestWriteResult:
    """Tests for write_result function."""

    def test_write_result_creates_file(self, temp_dir: Path) -> None:
        """Test that write_result creates a file."""
        result = ResultTask(
            feature_id="feat/test",
            agent_id="01-architect",
            output_text="Architecture design document",
            prompt_hash="abc123",
            output_hash="def456",
            timestamp=datetime.now(UTC),
        )

        path = write_result(temp_dir, "feat/test", "01-architect", result)

        assert path.exists()
        assert path.is_file()

    def test_write_result_creates_out_directory(self, temp_dir: Path) -> None:
        """Test that write_result creates out/ directory."""
        result = ResultTask("feat/test", "01-architect", "Output", "h1", "h2", datetime.now(UTC))

        path = write_result(temp_dir, "feat/test", "01-architect", result)

        # Verify it's in out/ directory
        assert path.parent.name == "out"
        expected_dir = temp_dir / "feat/test" / "01-architect" / "out"
        assert path.parent == expected_dir

    def test_write_result_filename_format(self, temp_dir: Path) -> None:
        """Test that result filename has correct format."""
        result = ResultTask("feat/test", "01-architect", "Output", "h1", "h2", datetime.now(UTC))

        path = write_result(temp_dir, "feat/test", "01-architect", result)

        # Should end with _result.md
        assert path.name.endswith("_result.md")

    def test_write_result_content(self, temp_dir: Path) -> None:
        """Test that written result contains audit frontmatter."""
        result = ResultTask(
            feature_id="feat/test",
            agent_id="01-architect",
            output_text="Architecture design document",
            prompt_hash="abc123hash",
            output_hash="def456hash",
            timestamp=datetime.now(UTC),
        )

        path = write_result(temp_dir, "feat/test", "01-architect", result)

        content = path.read_text()
        # Should have audit frontmatter
        assert "feature: feat/test" in content
        assert "agent: 01-architect" in content
        assert "prompt_hash: abc123hash" in content
        assert "output_hash: def456hash" in content
        assert "generated_at:" in content
        # Should have output text
        assert "Architecture design document" in content

    def test_write_result_with_real_hashes(self, temp_dir: Path) -> None:
        """Test writing result with actual SHA256 hashes."""
        prompt_text = "Design a system"
        output_text = "System architecture..."

        result = ResultTask(
            feature_id="feat/real",
            agent_id="02-openapi",
            output_text=output_text,
            prompt_hash=sha256_hash(prompt_text),
            output_hash=sha256_hash(output_text),
            timestamp=datetime.now(UTC),
        )

        path = write_result(temp_dir, "feat/real", "02-openapi", result)

        content = path.read_text()
        assert sha256_hash(prompt_text) in content
        assert sha256_hash(output_text) in content


class TestMarkProcessed:
    """Tests for mark_processed function."""

    def test_mark_processed_renames_file(self, temp_dir: Path) -> None:
        """Test that mark_processed renames file correctly."""
        prompt_file = temp_dir / "test_prompt.md"
        prompt_file.write_text("test content")

        processed = mark_processed(prompt_file)

        assert not prompt_file.exists()
        assert processed.exists()
        assert processed.suffix == ".processed"

    def test_mark_processed_preserves_content(self, temp_dir: Path) -> None:
        """Test that content is preserved after renaming."""
        prompt_file = temp_dir / "test_prompt.md"
        original_content = "test content with data"
        prompt_file.write_text(original_content)

        processed = mark_processed(prompt_file)

        assert processed.read_text() == original_content

    def test_mark_processed_returns_new_path(self, temp_dir: Path) -> None:
        """Test that mark_processed returns the new path."""
        prompt_file = temp_dir / "prompt.md"
        prompt_file.write_text("test")

        processed = mark_processed(prompt_file)

        assert processed == temp_dir / "prompt.processed"

    def test_mark_processed_file_not_found(self, temp_dir: Path) -> None:
        """Test mark_processed raises error for non-existent file."""
        nonexistent = temp_dir / "does-not-exist.md"

        with pytest.raises(FileNotFoundError, match="File not found"):
            mark_processed(nonexistent)

    def test_mark_processed_with_full_prompt(self, temp_dir: Path) -> None:
        """Test marking a real prompt file as processed."""
        prompt = PromptTask("feat/test", "01-architect", "Test prompt")
        path = write_prompt(temp_dir, "feat/test", "01-architect", prompt)

        processed = mark_processed(path)

        assert processed.suffix == ".processed"
        assert not path.exists()
        # Should still be readable
        content = processed.read_text()
        assert "Test prompt" in content


class TestListPendingPrompts:
    """Tests for list_pending_prompts function."""

    def test_list_pending_prompts_empty(self, temp_dir: Path) -> None:
        """Test listing when no prompts exist."""
        agent_dir = temp_dir / "feat/test" / "01-architect"

        pending = list_pending_prompts(agent_dir)

        assert pending == []

    def test_list_pending_prompts_no_in_directory(self, temp_dir: Path) -> None:
        """Test listing when in/ directory doesn't exist."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        agent_dir.mkdir(parents=True)

        pending = list_pending_prompts(agent_dir)

        assert pending == []

    def test_list_pending_prompts_single_file(self, temp_dir: Path) -> None:
        """Test listing with a single prompt file."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        in_dir = agent_dir / "in"
        in_dir.mkdir(parents=True)

        (in_dir / "prompt1.md").write_text("test")

        pending = list_pending_prompts(agent_dir)

        assert len(pending) == 1
        assert pending[0].name == "prompt1.md"

    def test_list_pending_prompts_multiple_files(self, temp_dir: Path) -> None:
        """Test listing multiple prompt files."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        in_dir = agent_dir / "in"
        in_dir.mkdir(parents=True)

        (in_dir / "prompt1.md").write_text("test1")
        time.sleep(0.01)  # Ensure different timestamps
        (in_dir / "prompt2.md").write_text("test2")
        time.sleep(0.01)
        (in_dir / "prompt3.md").write_text("test3")

        pending = list_pending_prompts(agent_dir)

        assert len(pending) == 3
        assert all(p.suffix == ".md" for p in pending)

    def test_list_pending_prompts_excludes_processed(self, temp_dir: Path) -> None:
        """Test that .processed files are excluded."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        in_dir = agent_dir / "in"
        in_dir.mkdir(parents=True)

        (in_dir / "prompt1.md").write_text("test1")
        (in_dir / "prompt2.md").write_text("test2")
        (in_dir / "prompt3.processed").write_text("test3")
        (in_dir / "prompt4.processed").write_text("test4")

        pending = list_pending_prompts(agent_dir)

        assert len(pending) == 2
        assert all(p.suffix == ".md" for p in pending)
        assert all("prompt3" not in p.name and "prompt4" not in p.name for p in pending)

    def test_list_pending_prompts_sorted_by_time(self, temp_dir: Path) -> None:
        """Test that prompts are sorted by creation time (oldest first)."""
        agent_dir = temp_dir / "feat/test" / "01-architect"
        in_dir = agent_dir / "in"
        in_dir.mkdir(parents=True)

        # Create files with delays to ensure different timestamps
        (in_dir / "prompt3.md").write_text("third")
        time.sleep(0.01)
        (in_dir / "prompt1.md").write_text("first")
        time.sleep(0.01)
        (in_dir / "prompt2.md").write_text("second")

        pending = list_pending_prompts(agent_dir)

        # Should be sorted by creation time, not name
        # prompt3 was created first, then prompt1, then prompt2
        assert pending[0].name == "prompt3.md"
        assert pending[1].name == "prompt1.md"
        assert pending[2].name == "prompt2.md"

    def test_list_pending_prompts_with_real_prompts(self, temp_dir: Path) -> None:
        """Test listing with actual written prompts."""
        prompt1 = PromptTask("feat/test", "01-architect", "First")
        prompt2 = PromptTask("feat/test", "01-architect", "Second")

        write_prompt(temp_dir, "feat/test", "01-architect", prompt1)
        time.sleep(0.01)
        write_prompt(temp_dir, "feat/test", "01-architect", prompt2)

        agent_dir = temp_dir / "feat/test" / "01-architect"
        pending = list_pending_prompts(agent_dir)

        assert len(pending) == 2
        assert all("_prompt.md" in p.name for p in pending)


class TestIntegration:
    """Integration tests combining multiple operations."""

    def test_full_workflow(self, temp_dir: Path) -> None:
        """Test complete workflow: write prompt, read, write result, mark processed."""
        # Write prompt
        prompt = PromptTask(
            feature_id="feat/workflow",
            agent_id="01-architect",
            prompt_text="Design a microservices architecture",
        )
        prompt_path = write_prompt(temp_dir, "feat/workflow", "01-architect", prompt)

        # Read prompt
        parsed_prompt = read_prompt(prompt_path)
        assert parsed_prompt.prompt_text == "Design a microservices architecture"

        # Write result
        result = ResultTask(
            feature_id="feat/workflow",
            agent_id="01-architect",
            output_text="Microservices architecture design...",
            prompt_hash=sha256_hash(prompt.prompt_text),
            output_hash=sha256_hash("Microservices architecture design..."),
            timestamp=datetime.now(UTC),
        )
        result_path = write_result(temp_dir, "feat/workflow", "01-architect", result)

        assert result_path.exists()
        assert result_path.parent.name == "out"

        # Mark as processed
        processed_path = mark_processed(prompt_path)
        assert processed_path.exists()
        assert not prompt_path.exists()

    def test_multiple_agents_workflow(self, temp_dir: Path) -> None:
        """Test workflow with multiple agents."""
        agents = ["01-architect", "02-openapi", "03-ui-skeleton"]

        for agent_id in agents:
            prompt = PromptTask("feat/multi", agent_id, f"Task for {agent_id}")
            write_prompt(temp_dir, "feat/multi", agent_id, prompt)

        # Verify each agent has their prompt
        for agent_id in agents:
            agent_dir = temp_dir / "feat/multi" / agent_id
            pending = list_pending_prompts(agent_dir)
            assert len(pending) == 1
            assert agent_id in str(pending[0])

    def test_queue_processing_order(self, temp_dir: Path) -> None:
        """Test that queue maintains FIFO order."""
        # Write multiple prompts
        for i in range(5):
            prompt = PromptTask("feat/queue", "01-architect", f"Prompt {i}")
            write_prompt(temp_dir, "feat/queue", "01-architect", prompt)
            time.sleep(0.01)  # Ensure different timestamps

        agent_dir = temp_dir / "feat/queue" / "01-architect"
        pending = list_pending_prompts(agent_dir)

        # Should be 5 prompts
        assert len(pending) == 5

        # Process first prompt
        first_prompt = pending[0]
        mark_processed(first_prompt)

        # Verify only 4 remain
        pending_after = list_pending_prompts(agent_dir)
        assert len(pending_after) == 4
        assert first_prompt not in pending_after
