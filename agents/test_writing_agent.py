"""Tests for writing_agent post-processing logic."""

from writing_agent import clean_post_body, _has_sections

# The broken body from 2026-03-19: Exa Search duplicated across 3 sections,
# Tutorials & Guides containing only "None."
BROKEN_BODY = """\
## Open Source Releases
**[unsloth](https://github.com/unslothai/unsloth)** — Fine-tuning framework for open-weight LLMs.

## AI Dev Tools
**[Exa Search](https://smithery.ai/servers/exa)** — Fast web search and crawling for AI agents.

## MCP Servers & Integrations
**[Exa Search](https://smithery.ai/servers/exa)** — Fast, intelligent web search and crawling capabilities for AI agents.

## Community Finds
**[Exa Search](https://smithery.ai/servers/exa)** — Fast, intelligent web search and crawling capabilities for AI agents.

## Tutorials & Guides
None.

## Today's Synthesis
Some synthesis paragraph here."""


def test_first_section_wins_for_duplicate_urls():
    result = clean_post_body(BROKEN_BODY)
    # Exa Search appears once (in AI Dev Tools, the first section it appeared in)
    assert result.count("smithery.ai/servers/exa") == 1
    assert "## AI Dev Tools" in result


def test_empty_sections_after_dedup_are_omitted():
    result = clean_post_body(BROKEN_BODY)
    assert "## MCP Servers & Integrations" not in result
    assert "## Community Finds" not in result


def test_none_literal_sections_are_omitted():
    result = clean_post_body(BROKEN_BODY)
    assert "## Tutorials & Guides" not in result
    assert "None." not in result


def test_sections_with_content_are_preserved():
    result = clean_post_body(BROKEN_BODY)
    assert "## Open Source Releases" in result
    assert "unsloth" in result
    assert "## Today's Synthesis" in result
    assert "Some synthesis paragraph here." in result


# --- _has_sections ---

WELL_FORMED_BODY = """\
## Model Releases
**[SomeModel](https://huggingface.co/org/SomeModel)** — A new model.

## Today's Synthesis
Some synthesis here."""

SYNTHESIS_ONLY_BODY = """\
**Today's Synthesis**
If you pair tool A with tool B you get something nice. See [tool-a](https://example.com/a)
and [tool-b](https://example.com/b) for details."""

EMPTY_SECTIONS_BODY = """\
## Model Releases

## Today's Synthesis
Some synthesis here."""


def test_has_sections_returns_true_for_well_formed_post():
    assert _has_sections(WELL_FORMED_BODY) is True


def test_has_sections_returns_false_for_synthesis_only():
    # Reproduces the 2026-03-20 failure: openrouter/free wrote only a synthesis blob
    assert _has_sections(SYNTHESIS_ONLY_BODY) is False


def test_has_sections_returns_false_when_sections_have_no_links():
    assert _has_sections(EMPTY_SECTIONS_BODY) is False
