"""Tests for weft.code.parser module."""

from weft.code.models import PatchAction
from weft.code.parser import has_code_patches, parse_code_from_markdown


class TestParseCodeFromMarkdown:
    """Tests for parse_code_from_markdown function."""

    def test_parse_single_code_block(self):
        """Test parsing a single code block with all metadata."""
        markdown = """```python path=src/main.py action=create
print("Hello, World!")
```"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 1
        assert patches[0].file_path == "src/main.py"
        assert patches[0].content == 'print("Hello, World!")'
        assert patches[0].language == "python"
        assert patches[0].action == PatchAction.CREATE

    def test_parse_multiple_code_blocks(self):
        """Test parsing multiple code blocks with different languages."""
        markdown = """
```typescript path=src/Button.tsx action=create
export const Button = () => <button />;
```

Some text in between.

```python path=api/views.py action=update
def handler():
    return {"ok": True}
```

More text.

```javascript path=utils/helper.js action=delete
// Legacy code
```
"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 3

        # First patch
        assert patches[0].file_path == "src/Button.tsx"
        assert patches[0].language == "typescript"
        assert patches[0].action == PatchAction.CREATE
        assert "Button" in patches[0].content

        # Second patch
        assert patches[1].file_path == "api/views.py"
        assert patches[1].language == "python"
        assert patches[1].action == PatchAction.UPDATE
        assert "handler" in patches[1].content

        # Third patch
        assert patches[2].file_path == "utils/helper.js"
        assert patches[2].language == "javascript"
        assert patches[2].action == PatchAction.DELETE

    def test_parse_with_default_action(self):
        """Test that action defaults to CREATE when not specified."""
        markdown = """```python path=src/new_file.py
def new_function():
    pass
```"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 1
        assert patches[0].action == PatchAction.CREATE

    def test_parse_preserves_content_exactly(self):
        """Test that content is preserved with whitespace (except trailing newlines)."""
        markdown = """```python path=src/test.py action=create
def function():
    # Indented comment
    if True:
        return "value"
```"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 1
        content = patches[0].content
        assert "def function():" in content
        assert "    # Indented comment" in content
        assert '        return "value"' in content
        # Trailing newline should be stripped
        assert not content.endswith("\n")

    def test_parse_empty_markdown(self):
        """Test parsing empty markdown returns empty list."""
        patches = parse_code_from_markdown("")
        assert patches == []

        patches = parse_code_from_markdown("   \n\n   ")
        assert patches == []

    def test_parse_no_metadata_blocks_ignored(self):
        """Test that regular code blocks without path= are ignored."""
        markdown = """
Regular code block without metadata:

```python
print("This should be ignored")
```

Code block with metadata:

```python path=src/main.py
print("This should be captured")
```
"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 1
        assert patches[0].file_path == "src/main.py"
        assert 'print("This should be captured")' in patches[0].content

    def test_parse_special_characters_in_path(self):
        """Test paths with special characters."""
        markdown = """```python path=src/utils/my-helper_v2.py action=create
# Helper
```"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 1
        assert patches[0].file_path == "src/utils/my-helper_v2.py"

    def test_parse_unicode_content(self):
        """Test that unicode characters in content are preserved."""
        markdown = """```python path=src/i18n.py action=create
GREETING = "Hello 世界 🌍"
```"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 1
        assert "世界" in patches[0].content
        assert "🌍" in patches[0].content

    def test_parse_invalid_action_defaults_to_create(self, caplog):
        """Test that invalid action falls back to CREATE with warning."""
        markdown = """```python path=src/test.py action=INVALID
# Code
```"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 1
        assert patches[0].action == PatchAction.CREATE
        # Check that warning was logged
        assert "Invalid action" in caplog.text
        assert "INVALID" in caplog.text

    def test_parse_malformed_code_fence(self):
        """Test that malformed code blocks result in unexpected content capture."""
        # When a code block is missing its closing fence, the regex will capture
        # content until it finds the next closing fence, resulting in malformed content
        markdown = """
```python path=src/test.py
print("Missing closing fence")

Text that should not be in the code block.
```

```python path=src/valid.py
print("Valid")
```
"""

        patches = parse_code_from_markdown(markdown)

        # Both blocks are captured, but the first has malformed content
        assert len(patches) == 2
        assert patches[0].file_path == "src/test.py"
        # First patch captures extra content due to missing fence
        assert "Text that should not be in the code block" in patches[0].content
        assert patches[1].file_path == "src/valid.py"
        assert patches[1].content == 'print("Valid")'

    def test_parse_action_case_insensitive(self):
        """Test that action values are case-insensitive."""
        test_cases = [
            ("CREATE", PatchAction.CREATE),
            ("create", PatchAction.CREATE),
            ("Create", PatchAction.CREATE),
            ("UPDATE", PatchAction.UPDATE),
            ("update", PatchAction.UPDATE),
            ("DELETE", PatchAction.DELETE),
            ("delete", PatchAction.DELETE),
        ]

        for action_str, expected_action in test_cases:
            markdown = f"""```python path=src/test.py action={action_str}
# Code
```"""
            patches = parse_code_from_markdown(markdown)
            assert len(patches) == 1
            assert patches[0].action == expected_action

    def test_parse_strips_trailing_newline(self):
        """Test that trailing newlines are stripped from content."""
        markdown = """```python path=src/test.py
def test():
    pass

```"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 1
        # Content should not end with newline
        assert not patches[0].content.endswith("\n")
        # But should still contain the function
        assert "def test():" in patches[0].content


class TestHasCodePatches:
    """Tests for has_code_patches function."""

    def test_has_patches_returns_true(self):
        """Test that function returns True when patches exist."""
        markdown = """```python path=src/main.py
print("Hello")
```"""

        assert has_code_patches(markdown) is True

    def test_has_patches_returns_false_for_plain_markdown(self):
        """Test that function returns False for plain markdown."""
        markdown = """# Title

Some text without code blocks.
"""

        assert has_code_patches(markdown) is False

    def test_has_patches_returns_false_for_regular_code_blocks(self):
        """Test that function returns False for code blocks without metadata."""
        markdown = """
```python
print("No path metadata")
```
"""

        assert has_code_patches(markdown) is False

    def test_has_patches_partial_match(self):
        """Test that partial matches don't trigger false positives."""
        markdown = """
The file has a path=something in text but no code fence.
```python
# Code without path= metadata
```
"""

        assert has_code_patches(markdown) is False


class TestSecurityCases:
    """Security tests for path handling."""

    def test_parse_path_traversal_attempt(self):
        """Test that path traversal attempts are parsed (validation happens elsewhere)."""
        markdown = """```python path=../../etc/passwd action=create
malicious content
```"""

        patches = parse_code_from_markdown(markdown)

        # Parser doesn't validate paths, just extracts them
        assert len(patches) == 1
        assert patches[0].file_path == "../../etc/passwd"
        # Note: Path validation should happen in applier, not parser

    def test_parse_absolute_paths(self):
        """Test that absolute paths are parsed (validation happens elsewhere)."""
        markdown = """```python path=/root/file.txt action=create
content
```"""

        patches = parse_code_from_markdown(markdown)

        # Parser extracts absolute paths as-is
        assert len(patches) == 1
        assert patches[0].file_path == "/root/file.txt"
        # Note: Path validation should happen in applier, not parser


class TestEdgeCases:
    """Additional edge case tests."""

    def test_parse_empty_content(self):
        """Test parsing code block with empty content."""
        markdown = """```python path=src/empty.py action=create
```"""

        patches = parse_code_from_markdown(markdown)

        assert len(patches) == 1
        assert patches[0].content == ""

    def test_parse_multiple_actions_same_file(self):
        """Test that multiple operations on same file are all extracted."""
        markdown = """
```python path=src/test.py action=create
# Version 1
```

```python path=src/test.py action=update
# Version 2
```
"""

        patches = parse_code_from_markdown(markdown)

        # Both patches should be extracted
        assert len(patches) == 2
        assert patches[0].action == PatchAction.CREATE
        assert patches[1].action == PatchAction.UPDATE
        assert patches[0].file_path == patches[1].file_path

    def test_parse_various_languages(self):
        """Test parsing different programming languages."""
        languages = [
            "python",
            "javascript",
            "typescript",
            "rust",
            "go",
            "java",
            "cpp",
            "ruby",
            "php",
        ]

        markdown_parts = []
        for lang in languages:
            markdown_parts.append(f"```{lang} path=src/file.{lang}\n// Code\n```")

        markdown = "\n\n".join(markdown_parts)
        patches = parse_code_from_markdown(markdown)

        assert len(patches) == len(languages)
        for i, lang in enumerate(languages):
            assert patches[i].language == lang
