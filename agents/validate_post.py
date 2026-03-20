#!/usr/bin/env python3
"""Validates that a generated post has the expected structure.

Exits 0 if valid, 1 if not. Used as a workflow gate before committing.
"""

import re
import sys
from pathlib import Path

MIN_ITEMS = 3


def validate(path: Path) -> list[str]:
    """Return a list of failure reasons, empty if valid."""
    if not path.exists():
        return [f"Post file not found: {path}"]

    text = path.read_text()

    # Strip front matter
    if text.startswith("---"):
        end = text.index("---", 3)
        body = text[end + 3:].lstrip("\n")
    else:
        body = text

    errors = []

    # Must have at least one ## section containing a markdown link
    sections_with_links = [
        s for s in re.split(r'(?=^## )', body, flags=re.MULTILINE)
        if s.startswith("## ") and re.search(r'\]\(https?://', s)
    ]
    if not sections_with_links:
        errors.append("No ## sections with linked items found")

    # Must have a minimum number of linked items across the whole post
    all_links = re.findall(r'\]\(https?://[^)]+\)', body)
    if len(all_links) < MIN_ITEMS:
        errors.append(f"Only {len(all_links)} linked items (minimum {MIN_ITEMS})")

    # Must have a synthesis section
    if "## Today's Synthesis" not in body and "Today's Synthesis" not in body:
        errors.append("Missing Today's Synthesis section")

    return errors


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: validate_post.py <post.md>", file=sys.stderr)
        sys.exit(1)

    path = Path(sys.argv[1])
    errors = validate(path)

    if errors:
        print(f"Post validation failed: {path}", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Post valid: {path}", file=sys.stderr)


if __name__ == "__main__":
    main()
