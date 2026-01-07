"""Cryptographic hashing and audit trail utilities."""

import hashlib
import re
from datetime import UTC, datetime


def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_audit_frontmatter(
    feature: str,
    agent: str,
    prompt_hash: str,
    output_hash: str,
    spec_version: str = "1.0.0",
    conversation_id: str | None = None,
) -> str:
    timestamp = datetime.now(UTC).isoformat().replace("+00:00", "Z")

    frontmatter = f"""---
feature: {feature}
agent: {agent}
prompt_spec_version: {spec_version}
generated_at: {timestamp}
prompt_hash: {prompt_hash}
output_hash: {output_hash}"""

    if conversation_id:
        frontmatter += f"\nconversation_id: {conversation_id}"

    frontmatter += "\n---\n"

    return frontmatter


def parse_audit_frontmatter(content: str) -> dict[str, str]:
    # Match frontmatter between --- delimiters at start of content
    pattern = r"^---\s*\n(.*?)\n---\s*\n"
    match = re.match(pattern, content, re.DOTALL)

    if not match:
        return {}

    frontmatter_text = match.group(1)
    metadata = {}

    # Parse simple YAML key-value pairs
    for line in frontmatter_text.split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue

        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()

    return metadata


def verify_audit_hash(content: str, expected_hash: str) -> bool:
    """Strips frontmatter before computing hash."""
    # Strip frontmatter if present
    pattern = r"^---\s*\n.*?\n---\s*\n"
    stripped_content = re.sub(pattern, "", content, count=1, flags=re.DOTALL)

    # Strip leading/trailing whitespace for comparison
    stripped_content = stripped_content.strip()

    # Compute hash of stripped content
    computed_hash = sha256_hash(stripped_content)

    return computed_hash == expected_hash
