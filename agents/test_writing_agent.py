"""Tests for writing_agent post-processing logic."""

from writing_agent import clean_post_body, _has_sections, _parse_qc_response, build_synthesis_prompt

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


# --- _parse_qc_response ---

def test_parse_qc_approved_returns_empty():
    assert _parse_qc_response('{"approved": true, "issues": []}') == []


def test_parse_qc_issues_returned_when_not_approved():
    resp = '{"approved": false, "issues": ["Bullet A restates its title", "Synthesis is vague"]}'
    assert _parse_qc_response(resp) == ["Bullet A restates its title", "Synthesis is vague"]


def test_parse_qc_extracts_json_from_prose():
    # Models sometimes wrap JSON in explanation text
    resp = 'After reviewing the post, here is my assessment:\n{"approved": false, "issues": ["Truncated sentence"]}\nHope that helps.'
    assert _parse_qc_response(resp) == ["Truncated sentence"]


def test_parse_qc_empty_issues_treated_as_approved():
    # approved=false but no issues — treat as approved to avoid empty revision
    assert _parse_qc_response('{"approved": false, "issues": []}') == []


def test_parse_qc_missing_approved_key_defaults_to_approved():
    # Malformed response missing "approved" key — fail open
    assert _parse_qc_response('{"issues": ["something"]}') == []


def test_parse_qc_invalid_json_returns_empty():
    assert _parse_qc_response("Sorry, I cannot review this post.") == []


def test_parse_qc_empty_string_returns_empty():
    assert _parse_qc_response("") == []


# --- build_synthesis_prompt ---

SAMPLE_BULLETS = """\
## Model Releases
**[SomeModel](https://huggingface.co/org/SomeModel)** — A capable new model.

## AI Dev Tools
**[some-tool](https://github.com/org/some-tool)** — A useful library."""


def test_build_synthesis_prompt_includes_bullets():
    prompt = build_synthesis_prompt(SAMPLE_BULLETS)
    assert "SomeModel" in prompt
    assert "some-tool" in prompt


def test_build_synthesis_prompt_no_holiday():
    prompt = build_synthesis_prompt(SAMPLE_BULLETS)
    assert "TODAY IS" not in prompt


def test_build_synthesis_prompt_includes_holiday():
    from unittest.mock import MagicMock
    holiday = MagicMock()
    holiday.name = "April Fools' Day"
    holiday.emoji = "🃏"
    prompt = build_synthesis_prompt(SAMPLE_BULLETS, holiday)
    assert "APRIL FOOLS' DAY" in prompt
    assert "🃏" in prompt
