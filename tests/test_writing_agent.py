"""Tests for writing agent logic — pure functions only, no LLM calls."""

import pytest

from writing_agent import (
    inject_april_fools_bullet,
    clean_post_body,
    build_writing_prompt,
    extract_tags,
    build_description,
    _APRIL_FOOLS_BULLET,
)
from holidays import get_holiday
from datetime import date


# ── inject_april_fools_bullet ────────────────────────────────────────────────

def test_inject_places_bullet_first_in_model_releases():
    body = "## Model Releases\n- **Some Model** — a real model.\n\n## Papers\n- **Paper** — stuff."
    result = inject_april_fools_bullet(body)
    lines = result.split("\n")
    assert lines[0] == "## Model Releases"
    assert lines[1] == _APRIL_FOOLS_BULLET
    assert "Some Model" in result  # existing content preserved


def test_inject_preserves_other_sections():
    body = "## Model Releases\n- **Real** — real.\n\n## Papers\n- **Paper** — stuff.\n\n## Today's Synthesis\nThings."
    result = inject_april_fools_bullet(body)
    assert "## Papers" in result
    assert "## Today's Synthesis" in result
    assert "Paper" in result


def test_inject_creates_model_releases_when_missing():
    body = "## Papers\n- **Paper** — stuff.\n\n## Today's Synthesis\nThings."
    result = inject_april_fools_bullet(body)
    assert result.startswith("## Model Releases\n" + _APRIL_FOOLS_BULLET)
    assert "## Papers" in result


def test_inject_bullet_contains_agi_link():
    body = "## Model Releases\n- **Real** — real."
    result = inject_april_fools_bullet(body)
    assert "https://tenkai.blog/tenkai-agi-1/" in result
    assert "TenkAI-AGI-1" in result


def test_inject_only_affects_first_model_releases_heading():
    """If Model Releases appears twice (shouldn't happen, but defensive), only first is touched."""
    body = "## Model Releases\n- **A** — a.\n\n## Model Releases\n- **B** — b."
    result = inject_april_fools_bullet(body)
    assert result.count(_APRIL_FOOLS_BULLET) == 1


# ── clean_post_body ──────────────────────────────────────────────────────────

def test_clean_deduplicates_urls_across_sections():
    body = (
        "## Model Releases\n"
        "- **[Foo](https://example.com/foo)** — first mention.\n\n"
        "## Papers\n"
        "- **[Foo Again](https://example.com/foo)** — duplicate url.\n"
        "- **[Bar](https://example.com/bar)** — unique.\n"
    )
    result = clean_post_body(body)
    assert result.count("https://example.com/foo") == 1
    assert "https://example.com/bar" in result


def test_clean_removes_empty_sections():
    body = (
        "## Model Releases\n"
        "- **[Real](https://example.com/real)** — something.\n\n"
        "## Papers\n\n"
        "## Today's Synthesis\n"
        "Connect things together."
    )
    result = clean_post_body(body)
    assert "## Papers" not in result
    assert "## Model Releases" in result
    assert "Today's Synthesis" in result


def test_clean_removes_none_sections():
    body = (
        "## Model Releases\n"
        "None.\n\n"
        "## Papers\n"
        "- **[Real](https://example.com/r)** — something.\n"
    )
    result = clean_post_body(body)
    assert "## Model Releases" not in result
    assert "## Papers" in result


def test_clean_preserves_content_without_urls():
    """Sections with no links (e.g. synthesis prose) are kept."""
    body = (
        "## Model Releases\n"
        "- **[Foo](https://example.com/foo)** — something.\n\n"
        "## Today's Synthesis\n"
        "This is a paragraph with no links that should be preserved."
    )
    result = clean_post_body(body)
    assert "Today's Synthesis" in result
    assert "paragraph with no links" in result


# ── build_writing_prompt ─────────────────────────────────────────────────────

def _make_research(*categories):
    """Build a minimal research dict with items in the given categories."""
    return {
        "date": "2026-04-01",
        "source": [
            {"title": f"Item {i}", "url": f"https://example.com/{i}",
             "summary": "A summary.", "category": cat, "relevance_score": 8}
            for i, cat in enumerate(categories)
        ],
    }


def test_prompt_without_holiday_has_no_holiday_header():
    research = _make_research("model", "paper")
    prompt = build_writing_prompt(research, holiday=None)
    assert "TODAY IS" not in prompt
    assert "Items are pre-organized" in prompt


def test_prompt_with_holiday_injects_theme():
    holiday = get_holiday(date(2026, 3, 14))  # Pi Day
    research = _make_research("model", "paper")
    prompt = build_writing_prompt(research, holiday=holiday)
    assert "PI DAY" in prompt.upper()
    assert holiday.theme[:30] in prompt


def test_prompt_sections_appear_in_order():
    research = _make_research("paper", "model", "mcp")
    prompt = build_writing_prompt(research, holiday=None)
    model_pos = prompt.index("## Model Releases")
    paper_pos = prompt.index("## Research Worth Reading")
    mcp_pos = prompt.index("## MCP Servers")
    assert model_pos < paper_pos < mcp_pos


def test_prompt_omits_empty_sections():
    research = _make_research("model")  # only model items
    prompt = build_writing_prompt(research, holiday=None)
    assert "## Research Worth Reading" not in prompt
    assert "## Model Releases" in prompt


def test_prompt_always_ends_with_synthesis():
    research = _make_research("model", "paper")
    prompt = build_writing_prompt(research, holiday=None)
    assert "## Today's Synthesis" in prompt
    assert prompt.rstrip().endswith("Use full markdown links.")


# ── extract_tags ─────────────────────────────────────────────────────────────

def test_extract_tags_always_includes_base_tags():
    tags = extract_tags([{"category": "model"}])
    assert "llm" in tags
    assert "open-source" in tags


def test_extract_tags_maps_categories():
    tags = extract_tags([
        {"category": "paper"},
        {"category": "dev-tool"},
        {"category": "discussion"},
    ])
    assert "papers" in tags
    assert "dev-tools" in tags
    assert "community" in tags


def test_extract_tags_deduplicates():
    # model and release both map to "releases"
    tags = extract_tags([{"category": "model"}, {"category": "release"}])
    assert tags.count("releases") == 1


# ── build_description ────────────────────────────────────────────────────────

def test_build_description_uses_first_two_titles():
    items = [
        {"title": "Alpha"},
        {"title": "Beta"},
        {"title": "Gamma"},
    ]
    desc = build_description(items)
    assert "Alpha" in desc
    assert "Beta" in desc
    assert "Gamma" not in desc
    assert "and more" in desc


def test_build_description_fallback_on_empty():
    assert build_description([]) == "Daily AI development digest"
