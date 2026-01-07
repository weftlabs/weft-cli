"""Tests for task queue data models."""

from datetime import UTC, datetime

import pytest

from weft.audit.hashing import sha256_hash
from weft.queue.models import (
    PromptTask,
    ResultTask,
    TaskStatus,
    markdown_to_prompt,
    prompt_to_markdown,
    result_to_markdown,
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_task_status_values(self) -> None:
        """Test that TaskStatus has all required values."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.PROCESSING.value == "processing"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.ERROR.value == "error"

    def test_task_status_enum_members(self) -> None:
        """Test that all enum members exist."""
        statuses = [status.value for status in TaskStatus]
        assert "pending" in statuses
        assert "processing" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "error" in statuses


class TestPromptTask:
    """Tests for PromptTask dataclass."""

    def test_prompt_task_creation(self) -> None:
        """Test creating a PromptTask with all fields."""
        prompt = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Design a user authentication system",
            spec_version="1.0.0",
            revision=1,
        )

        assert prompt.feature_id == "feat/test"
        assert prompt.agent_id == "01-architect"
        assert prompt.prompt_text == "Design a user authentication system"
        assert prompt.spec_version == "1.0.0"
        assert prompt.revision == 1

    def test_prompt_task_defaults(self) -> None:
        """Test PromptTask uses default values."""
        prompt = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Test prompt",
        )

        assert prompt.spec_version == "1.0.0"
        assert prompt.revision is None

    def test_prompt_task_custom_values(self) -> None:
        """Test PromptTask with custom spec_version and revision."""
        prompt = PromptTask(
            feature_id="feat/custom",
            agent_id="02-openapi",
            prompt_text="Custom prompt",
            spec_version="2.1.0",
            revision=5,
        )

        assert prompt.spec_version == "2.1.0"
        assert prompt.revision == 5


class TestResultTask:
    """Tests for ResultTask dataclass."""

    def test_result_task_creation(self) -> None:
        """Test creating a ResultTask with all fields."""
        timestamp = datetime.now(UTC)
        result = ResultTask(
            feature_id="feat/test",
            agent_id="01-architect",
            output_text="Architecture design document...",
            prompt_hash="abc123",
            output_hash="def456",
            timestamp=timestamp,
        )

        assert result.feature_id == "feat/test"
        assert result.agent_id == "01-architect"
        assert result.output_text == "Architecture design document..."
        assert result.prompt_hash == "abc123"
        assert result.output_hash == "def456"
        assert result.timestamp == timestamp

    def test_result_task_with_real_hashes(self) -> None:
        """Test ResultTask with actual SHA256 hashes."""
        prompt_text = "Design a system"
        output_text = "System design..."
        prompt_hash = sha256_hash(prompt_text)
        output_hash = sha256_hash(output_text)

        result = ResultTask(
            feature_id="feat/real-hash",
            agent_id="01-architect",
            output_text=output_text,
            prompt_hash=prompt_hash,
            output_hash=output_hash,
            timestamp=datetime.now(UTC),
        )

        assert len(result.prompt_hash) == 64
        assert len(result.output_hash) == 64


class TestPromptToMarkdown:
    """Tests for prompt_to_markdown function."""

    def test_prompt_to_markdown_basic(self) -> None:
        """Test basic prompt serialization."""
        prompt = PromptTask(
            feature_id="feat/test",
            agent_id="01-architect",
            prompt_text="Design a user auth system",
        )

        markdown = prompt_to_markdown(prompt)

        assert markdown.startswith("---\n")
        assert "feature: feat/test" in markdown
        assert "agent: 01-architect" in markdown
        assert "prompt_spec_version: 1.0.0" in markdown
        assert "revision" not in markdown  # revision is None, so not serialized
        assert "Design a user auth system" in markdown
        assert markdown.count("---") == 2

    def test_prompt_to_markdown_multiline(self) -> None:
        """Test prompt with multiline text."""
        prompt = PromptTask(
            feature_id="feat/multiline",
            agent_id="02-openapi",
            prompt_text="Line 1\nLine 2\nLine 3",
        )

        markdown = prompt_to_markdown(prompt)

        assert "Line 1" in markdown
        assert "Line 2" in markdown
        assert "Line 3" in markdown

    def test_prompt_to_markdown_custom_version(self) -> None:
        """Test prompt with custom spec version."""
        prompt = PromptTask(
            feature_id="feat/custom",
            agent_id="01-architect",
            prompt_text="Test",
            spec_version="2.0.0",
            revision=3,
        )

        markdown = prompt_to_markdown(prompt)

        assert "prompt_spec_version: 2.0.0" in markdown
        assert "revision: 3" in markdown

    def test_prompt_to_markdown_special_chars(self) -> None:
        """Test prompt with special characters."""
        prompt = PromptTask(
            feature_id="feat/special",
            agent_id="01-architect",
            prompt_text='Test with: colons, quotes "test", and symbols @#$',
        )

        markdown = prompt_to_markdown(prompt)

        assert "colons" in markdown
        assert "quotes" in markdown
        assert "symbols" in markdown


class TestMarkdownToPrompt:
    """Tests for markdown_to_prompt function."""

    def test_markdown_to_prompt_basic(self) -> None:
        """Test basic markdown parsing."""
        content = """---
feature: feat/test
agent: 01-architect
prompt_spec_version: 1.0.0
revision: 1
---

Design a user authentication system"""

        prompt = markdown_to_prompt(content)

        assert prompt.feature_id == "feat/test"
        assert prompt.agent_id == "01-architect"
        assert prompt.spec_version == "1.0.0"
        assert prompt.revision == 1
        assert prompt.prompt_text == "Design a user authentication system"

    def test_markdown_to_prompt_defaults(self) -> None:
        """Test markdown parsing with optional fields missing."""
        content = """---
feature: feat/minimal
agent: 02-openapi
---

Minimal prompt"""

        prompt = markdown_to_prompt(content)

        assert prompt.feature_id == "feat/minimal"
        assert prompt.agent_id == "02-openapi"
        assert prompt.spec_version == "1.0.0"  # Default
        assert prompt.revision == 1  # Default
        assert prompt.prompt_text == "Minimal prompt"

    def test_markdown_to_prompt_multiline(self) -> None:
        """Test parsing multiline prompt text."""
        content = """---
feature: feat/multi
agent: 01-architect
---

Line 1
Line 2
Line 3"""

        prompt = markdown_to_prompt(content)

        assert "Line 1" in prompt.prompt_text
        assert "Line 2" in prompt.prompt_text
        assert "Line 3" in prompt.prompt_text

    def test_markdown_to_prompt_invalid_no_delimiters(self) -> None:
        """Test parsing fails without frontmatter delimiters."""
        content = "Just some text without frontmatter"

        with pytest.raises(ValueError, match="missing frontmatter delimiters"):
            markdown_to_prompt(content)

    def test_markdown_to_prompt_invalid_yaml(self) -> None:
        """Test parsing fails with invalid YAML."""
        content = """---
invalid: yaml: with: too: many: colons:
---

Prompt text"""

        with pytest.raises(ValueError, match="Invalid YAML frontmatter"):
            markdown_to_prompt(content)

    def test_markdown_to_prompt_missing_feature(self) -> None:
        """Test parsing fails without required 'feature' field."""
        content = """---
agent: 01-architect
---

Prompt text"""

        with pytest.raises(ValueError, match="Missing required field 'feature'"):
            markdown_to_prompt(content)

    def test_markdown_to_prompt_missing_agent(self) -> None:
        """Test parsing fails without required 'agent' field."""
        content = """---
feature: feat/test
---

Prompt text"""

        with pytest.raises(ValueError, match="Missing required field 'agent'"):
            markdown_to_prompt(content)

    def test_markdown_to_prompt_empty_frontmatter(self) -> None:
        """Test parsing with empty frontmatter."""
        content = """---
---

Prompt text"""

        with pytest.raises(ValueError, match="Frontmatter must be a YAML dictionary"):
            markdown_to_prompt(content)


class TestResultToMarkdown:
    """Tests for result_to_markdown function."""

    def test_result_to_markdown_basic(self) -> None:
        """Test basic result serialization."""
        result = ResultTask(
            feature_id="feat/test",
            agent_id="01-architect",
            output_text="Architecture design document",
            prompt_hash="abc123",
            output_hash="def456",
            timestamp=datetime.now(UTC),
        )

        markdown = result_to_markdown(result)

        assert markdown.startswith("---\n")
        assert "feature: feat/test" in markdown
        assert "agent: 01-architect" in markdown
        assert "prompt_hash: abc123" in markdown
        assert "output_hash: def456" in markdown
        assert "generated_at:" in markdown
        assert "Architecture design document" in markdown

    def test_result_to_markdown_multiline(self) -> None:
        """Test result with multiline output."""
        result = ResultTask(
            feature_id="feat/multi",
            agent_id="02-openapi",
            output_text="# API Design\n\n## Endpoints\n\n- GET /api/users",
            prompt_hash="hash1",
            output_hash="hash2",
            timestamp=datetime.now(UTC),
        )

        markdown = result_to_markdown(result)

        assert "# API Design" in markdown
        assert "## Endpoints" in markdown
        assert "- GET /api/users" in markdown

    def test_result_to_markdown_with_real_hashes(self) -> None:
        """Test result serialization with actual hashes."""
        prompt_text = "Design an API"
        output_text = "API Design Document"

        prompt_hash = sha256_hash(prompt_text)
        output_hash = sha256_hash(output_text)

        result = ResultTask(
            feature_id="feat/real",
            agent_id="02-openapi",
            output_text=output_text,
            prompt_hash=prompt_hash,
            output_hash=output_hash,
            timestamp=datetime.now(UTC),
        )

        markdown = result_to_markdown(result)

        assert prompt_hash in markdown
        assert output_hash in markdown
        assert len(prompt_hash) == 64
        assert len(output_hash) == 64


class TestRoundTrip:
    """Integration tests for serialization round-trips."""

    def test_prompt_roundtrip(self) -> None:
        """Test PromptTask serialization and deserialization."""
        original = PromptTask(
            feature_id="feat/roundtrip",
            agent_id="01-architect",
            prompt_text="Design a microservices architecture",
            spec_version="1.2.3",
            revision=7,
        )

        # Serialize to markdown
        markdown = prompt_to_markdown(original)

        # Deserialize back
        parsed = markdown_to_prompt(markdown)

        # Should match original
        assert parsed.feature_id == original.feature_id
        assert parsed.agent_id == original.agent_id
        assert parsed.prompt_text == original.prompt_text
        assert parsed.spec_version == original.spec_version
        assert parsed.revision == original.revision

    def test_prompt_roundtrip_with_defaults(self) -> None:
        """Test roundtrip with default values.

        When revision is None, it's not serialized. When deserialized,
        missing revision field defaults to 1.
        """
        original = PromptTask(
            feature_id="feat/default",
            agent_id="03-ui-skeleton",
            prompt_text="Create UI components",
        )

        markdown = prompt_to_markdown(original)
        parsed = markdown_to_prompt(markdown)

        assert parsed.feature_id == original.feature_id
        assert parsed.agent_id == original.agent_id
        assert parsed.prompt_text == original.prompt_text
        assert parsed.spec_version == "1.0.0"
        # Original had revision=None, not serialized, so defaults to 1 on parse
        assert parsed.revision == 1

    def test_prompt_roundtrip_complex_text(self) -> None:
        """Test roundtrip with complex prompt text."""
        original = PromptTask(
            feature_id="feat/complex",
            agent_id="01-architect",
            prompt_text="""Design a system with:
- User authentication
- Role-based access control
- API rate limiting
- Caching strategy

Consider scalability and security.""",
        )

        markdown = prompt_to_markdown(original)
        parsed = markdown_to_prompt(markdown)

        assert parsed.prompt_text == original.prompt_text
