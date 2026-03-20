"""Tests for validate_post structure checks."""

import textwrap
from pathlib import Path

import pytest

from validate_post import validate

FRONT_MATTER = """\
---
title: "Tenkai Daily — March 20, 2026"
date: 2026-03-20
draft: false
tags: [llm, releases]
description: "Today: Foo and more."
---
"""

VALID_BODY = """\
## Model Releases
**[SomeModel](https://huggingface.co/org/SomeModel)** — A capable new model.

**[OtherModel](https://huggingface.co/org/OtherModel)** — Another one.

## AI Dev Tools
**[some-tool](https://github.com/org/some-tool)** — A useful library.

## Today's Synthesis
Pair SomeModel with some-tool for faster iteration."""

SYNTHESIS_ONLY_BODY = """\
**Today's Synthesis**
If you pair [tool-a](https://example.com/a) with [tool-b](https://example.com/b) you get something nice."""

NO_SYNTHESIS_BODY = """\
## Model Releases
**[SomeModel](https://huggingface.co/org/SomeModel)** — A capable new model.

**[OtherModel](https://huggingface.co/org/OtherModel)** — Another one.

**[ThirdModel](https://huggingface.co/org/ThirdModel)** — A third one."""


@pytest.fixture
def post_file(tmp_path):
    def _write(body: str, with_front_matter: bool = True) -> Path:
        content = (FRONT_MATTER + "\n" + body) if with_front_matter else body
        p = tmp_path / "2026-03-20.md"
        p.write_text(content)
        return p
    return _write


def test_valid_post_passes(post_file):
    assert validate(post_file(VALID_BODY)) == []


def test_missing_file_fails():
    errors = validate(Path("/tmp/nonexistent-post.md"))
    assert any("not found" in e for e in errors)


def test_synthesis_only_fails(post_file):
    # Reproduces 2026-03-20: openrouter/free wrote only a synthesis blob
    errors = validate(post_file(SYNTHESIS_ONLY_BODY))
    assert any("sections" in e for e in errors)


def test_no_synthesis_fails(post_file):
    errors = validate(post_file(NO_SYNTHESIS_BODY))
    assert any("Synthesis" in e for e in errors)


def test_too_few_items_fails(post_file):
    sparse = textwrap.dedent("""\
        ## Model Releases
        **[OnlyOne](https://huggingface.co/org/OnlyOne)** — Just one item.

        ## Today's Synthesis
        Not much to synthesize.""")
    errors = validate(post_file(sparse))
    assert any("items" in e for e in errors)
