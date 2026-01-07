"""Tests for audit hashing and frontmatter utilities."""

import re
from datetime import datetime

from weft.audit.hashing import (
    create_audit_frontmatter,
    parse_audit_frontmatter,
    sha256_hash,
    verify_audit_hash,
)


class TestSha256Hash:
    """Tests for sha256_hash function."""

    def test_hash_consistency(self) -> None:
        """Test that same input produces same hash."""
        text = "test prompt"
        hash1 = sha256_hash(text)
        hash2 = sha256_hash(text)

        assert hash1 == hash2

    def test_hash_length(self) -> None:
        """Test that hash is 64 characters (256 bits in hex)."""
        text = "any text"
        result = sha256_hash(text)

        assert len(result) == 64

    def test_hash_format(self) -> None:
        """Test that hash is valid hexadecimal."""
        text = "test"
        result = sha256_hash(text)

        # Should be all hex characters (0-9, a-f)
        assert re.match(r"^[0-9a-f]{64}$", result)

    def test_hash_known_value(self) -> None:
        """Test hash against known SHA256 value."""
        # Known SHA256 hash of "hello"
        expected = "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        result = sha256_hash("hello")

        assert result == expected

    def test_hash_empty_string(self) -> None:
        """Test hashing empty string."""
        result = sha256_hash("")

        # Known SHA256 hash of empty string
        expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        assert result == expected

    def test_hash_unicode(self) -> None:
        """Test hashing unicode characters."""
        text = "Hello world with unicode café"
        result = sha256_hash(text)

        # Should handle unicode without errors
        assert len(result) == 64
        assert re.match(r"^[0-9a-f]{64}$", result)

    def test_hash_different_inputs(self) -> None:
        """Test that different inputs produce different hashes."""
        hash1 = sha256_hash("text1")
        hash2 = sha256_hash("text2")

        assert hash1 != hash2

    def test_hash_multiline(self) -> None:
        """Test hashing multiline text."""
        text = """Line 1
Line 2
Line 3"""
        result = sha256_hash(text)

        assert len(result) == 64


class TestCreateAuditFrontmatter:
    """Tests for create_audit_frontmatter function."""

    def test_frontmatter_structure(self) -> None:
        """Test frontmatter has correct structure."""
        fm = create_audit_frontmatter("feat/test", "01-architect", "prompt123", "output456")

        # Should start and end with ---
        assert fm.startswith("---\n")
        assert fm.endswith("---\n")

        # Should have exactly 2 occurrences of ---
        assert fm.count("---") == 2

    def test_frontmatter_fields(self) -> None:
        """Test all required fields are present."""
        fm = create_audit_frontmatter(
            "feat/test", "01-architect", "prompt123", "output456", "1.0.0"
        )

        assert "feature: feat/test" in fm
        assert "agent: 01-architect" in fm
        assert "prompt_hash: prompt123" in fm
        assert "output_hash: output456" in fm
        assert "prompt_spec_version: 1.0.0" in fm
        assert "generated_at:" in fm

    def test_frontmatter_timestamp_format(self) -> None:
        """Test timestamp is in ISO 8601 format with UTC."""
        fm = create_audit_frontmatter("feat/test", "01-architect", "hash1", "hash2")

        # Extract timestamp
        match = re.search(r"generated_at: (.+)", fm)
        assert match is not None

        timestamp_str = match.group(1)

        # Should end with Z for UTC
        assert timestamp_str.endswith("Z")

        # Should be parseable as ISO 8601
        # Remove Z and add +00:00 for parsing
        timestamp_str_for_parse = timestamp_str.replace("Z", "+00:00")
        datetime.fromisoformat(timestamp_str_for_parse)

    def test_frontmatter_default_spec_version(self) -> None:
        """Test default spec version is 1.0.0."""
        fm = create_audit_frontmatter("feat/test", "01-architect", "h1", "h2")

        assert "prompt_spec_version: 1.0.0" in fm

    def test_frontmatter_custom_spec_version(self) -> None:
        """Test custom spec version is used."""
        fm = create_audit_frontmatter("feat/test", "01-architect", "h1", "h2", "2.3.4")

        assert "prompt_spec_version: 2.3.4" in fm

    def test_frontmatter_special_characters(self) -> None:
        """Test frontmatter with special characters in values."""
        fm = create_audit_frontmatter("feat/test-123", "01-architect", "abc!@#", "def$%^")

        assert "feature: feat/test-123" in fm
        assert "prompt_hash: abc!@#" in fm
        assert "output_hash: def$%^" in fm


class TestParseAuditFrontmatter:
    """Tests for parse_audit_frontmatter function."""

    def test_parse_basic_frontmatter(self) -> None:
        """Test parsing basic frontmatter."""
        content = """---
feature: feat/test
agent: 01-architect
---

Content here"""

        metadata = parse_audit_frontmatter(content)

        assert metadata["feature"] == "feat/test"
        assert metadata["agent"] == "01-architect"

    def test_parse_all_fields(self) -> None:
        """Test parsing all expected fields."""
        content = """---
feature: feat/user-auth
agent: 02-openapi
prompt_spec_version: 1.0.0
generated_at: 2025-12-11T21:00:00Z
prompt_hash: abc123
output_hash: def456
---

Content"""

        metadata = parse_audit_frontmatter(content)

        assert metadata["feature"] == "feat/user-auth"
        assert metadata["agent"] == "02-openapi"
        assert metadata["prompt_spec_version"] == "1.0.0"
        assert metadata["generated_at"] == "2025-12-11T21:00:00Z"
        assert metadata["prompt_hash"] == "abc123"
        assert metadata["output_hash"] == "def456"

    def test_parse_no_frontmatter(self) -> None:
        """Test parsing content without frontmatter."""
        content = "Just regular content"

        metadata = parse_audit_frontmatter(content)

        assert metadata == {}

    def test_parse_empty_frontmatter(self) -> None:
        """Test parsing empty frontmatter."""
        content = """---
---

Content"""

        metadata = parse_audit_frontmatter(content)

        assert metadata == {}

    def test_parse_with_extra_whitespace(self) -> None:
        """Test parsing with extra whitespace."""
        content = """---
feature:   feat/test
agent:  01-architect
---

Content"""

        metadata = parse_audit_frontmatter(content)

        assert metadata["feature"] == "feat/test"
        assert metadata["agent"] == "01-architect"

    def test_parse_with_colon_in_value(self) -> None:
        """Test parsing when value contains colons."""
        content = """---
generated_at: 2025-12-11T21:00:00Z
url: https://example.com:8080
---

Content"""

        metadata = parse_audit_frontmatter(content)

        assert metadata["generated_at"] == "2025-12-11T21:00:00Z"
        assert metadata["url"] == "https://example.com:8080"

    def test_parse_malformed_frontmatter(self) -> None:
        """Test parsing malformed frontmatter."""
        content = """---
no colon here
feature: feat/test
---

Content"""

        metadata = parse_audit_frontmatter(content)

        # Should still parse valid lines
        assert metadata["feature"] == "feat/test"

    def test_parse_frontmatter_not_at_start(self) -> None:
        """Test that frontmatter must be at start of content."""
        content = """Some text first
---
feature: feat/test
---

Content"""

        metadata = parse_audit_frontmatter(content)

        # Should not find frontmatter
        assert metadata == {}


class TestVerifyAuditHash:
    """Tests for verify_audit_hash function."""

    def test_verify_content_without_frontmatter(self) -> None:
        """Test verification of content without frontmatter."""
        content = "Actual content"
        expected_hash = sha256_hash("Actual content")

        assert verify_audit_hash(content, expected_hash)

    def test_verify_content_with_frontmatter(self) -> None:
        """Test verification strips frontmatter before hashing."""
        content = """---
metadata: here
---

Actual content"""

        expected_hash = sha256_hash("Actual content")

        assert verify_audit_hash(content, expected_hash)

    def test_verify_with_complete_frontmatter(self) -> None:
        """Test verification with complete audit frontmatter."""
        content = """---
feature: feat/test
agent: 01-architect
prompt_spec_version: 1.0.0
generated_at: 2025-12-11T21:00:00Z
prompt_hash: abc123
output_hash: def456
---

This is the actual output content."""

        expected_hash = sha256_hash("This is the actual output content.")

        assert verify_audit_hash(content, expected_hash)

    def test_verify_multiline_content(self) -> None:
        """Test verification with multiline content."""
        content = """---
metadata: here
---

Line 1
Line 2
Line 3"""

        expected_hash = sha256_hash("Line 1\nLine 2\nLine 3")

        assert verify_audit_hash(content, expected_hash)

    def test_verify_fails_with_wrong_hash(self) -> None:
        """Test verification fails with incorrect hash."""
        content = """---
metadata: here
---

Actual content"""

        wrong_hash = sha256_hash("Different content")

        assert not verify_audit_hash(content, wrong_hash)

    def test_verify_fails_with_tampered_content(self) -> None:
        """Test verification fails if content is tampered."""

        original_hash = sha256_hash("Original content")

        # Tamper with content
        tampered_content = """---
metadata: here
---

Tampered content"""

        assert not verify_audit_hash(tampered_content, original_hash)

    def test_verify_strips_whitespace(self) -> None:
        """Test that verification strips leading/trailing whitespace."""
        content = """---
metadata: here
---

  Content with whitespace
"""

        expected_hash = sha256_hash("Content with whitespace")

        assert verify_audit_hash(content, expected_hash)

    def test_verify_empty_content(self) -> None:
        """Test verification with empty content after frontmatter."""
        content = """---
metadata: here
---

"""

        expected_hash = sha256_hash("")

        assert verify_audit_hash(content, expected_hash)

    def test_verify_unicode_content(self) -> None:
        """Test verification with unicode content."""
        content = """---
metadata: here
---

Hello world with unicode café"""

        expected_hash = sha256_hash("Hello world with unicode café")

        assert verify_audit_hash(content, expected_hash)


class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_full_audit_workflow(self) -> None:
        """Test complete audit trail workflow."""
        # Create prompt and output
        prompt = "Design a user authentication system"
        output = "## Authentication Design\n\nUse JWT tokens..."

        # Hash them
        prompt_hash = sha256_hash(prompt)
        output_hash = sha256_hash(output)

        # Create frontmatter
        frontmatter = create_audit_frontmatter(
            "feat/user-auth", "01-architect", prompt_hash, output_hash, "1.0.0"
        )

        # Combine frontmatter with output
        full_output = frontmatter + "\n" + output

        # Parse frontmatter back
        metadata = parse_audit_frontmatter(full_output)

        assert metadata["feature"] == "feat/user-auth"
        assert metadata["agent"] == "01-architect"
        assert metadata["prompt_hash"] == prompt_hash
        assert metadata["output_hash"] == output_hash

        # Verify hash
        assert verify_audit_hash(full_output, output_hash)

    def test_hash_consistency_across_functions(self) -> None:
        """Test that hash functions are consistent."""
        text = "test content"

        hash1 = sha256_hash(text)

        # Create content with frontmatter
        content = f"""---
test: value
---

{text}"""

        # Verify should work with the hash of just the text
        assert verify_audit_hash(content, hash1)
