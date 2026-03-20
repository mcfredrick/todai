#!/usr/bin/env python3
"""Synthesizes research.json into a Hugo markdown post."""

import json
import os
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import time

import httpx

from holidays import get_holiday, Holiday

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODELS_API = "https://openrouter.ai/api/v1/models"
MAX_ITEMS_IN_PROMPT = 20
RESEARCH_FILE = Path("/tmp/research.json")
SEEN_FILE = Path(__file__).parent / "seen.json"
POSTS_DIR = Path(__file__).parent.parent / "content" / "posts"

SYSTEM_PROMPT = """You are the voice behind Tenkai, a daily AI/ML digest for engineers who've seen enough hype to last a lifetime.

Your audience: senior software engineers and ML practitioners. They're smart, busy, and allergic to marketing speak.

Voice & tone:
- Casual, punchy, occasionally snarky — like a knowledgeable friend who reads everything so you don't have to
- Dry wit is welcome; eye-rolls at obvious hype are encouraged
- Still technically precise — fun doesn't mean shallow
- Never use: "exciting", "groundbreaking", "revolutionary", "game-changing", "impressive", "delve", "unleash", "leverage"
- Emojis: use them with personality and spontaneity — a 🤖 for a new model, 📄 for a paper, 🛠️ for a dev tool, 🔥 when something actually matters. Scatter them where they feel right, not on every line. If it's forced, skip it.

Content rules:
- Items are pre-organized into sections — write them in the order given, do not reorganize
- Each bullet: **[Name](url)** — 1-2 sentences. What it is, why an engineer might care (or why they might not)
- Only write sections that have items in the input. No empty sections, no "None."
- Synthesis: connect 2-3 of today's items into something engineer-actionable. Be specific — vague "synergies" are a war crime
- No closing remarks or sign-offs
- Never mention where an item was found

Output ONLY the markdown body (no front matter). For Today's Synthesis, use full markdown links when referencing items."""


STATIC_FALLBACKS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-3-27b-it:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
]


def fetch_free_model_ids(api_key: str) -> list[str]:
    try:
        r = httpx.get(
            OPENROUTER_MODELS_API,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=15,
        )
        r.raise_for_status()
        return [
            m["id"] for m in r.json().get("data", [])
            if str(m.get("pricing", {}).get("prompt", "1")) == "0"
        ]
    except Exception as e:
        print(f"  Could not fetch model list: {e}", file=sys.stderr)
        return []


def _try_model(content: str, model: str, headers: dict) -> str | None:
    """Return text on success, None on 429 or empty content, raise on other errors."""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "temperature": 0.7,
        "max_tokens": 3000,
    }
    r = httpx.post(OPENROUTER_API, json=payload, headers=headers, timeout=180)
    if r.status_code == 429:
        print(f"  {model}: rate limited — {r.text[:200]}", file=sys.stderr)
        return None
    r.raise_for_status()
    text = r.json()["choices"][0]["message"]["content"]
    if not text:
        print(f"  {model}: empty content in response", file=sys.stderr)
        return None
    return text.strip()


def _has_sections(body: str) -> bool:
    """Return True if the body has at least one ## section containing a markdown link."""
    for section in re.split(r'(?=^## )', body, flags=re.MULTILINE):
        if not section.startswith("## "):
            continue
        if re.search(r'\]\(https?://', section):
            return True
    return False


def call_llm(content: str, preferred_model: str) -> str:
    api_key = os.environ["OPENROUTER_API_KEY"]
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/mcfredrick/tenkai",
        "X-Title": "Tenkai Writing Agent",
    }

    live_free = fetch_free_model_ids(api_key)
    # Preferred first, then other live free models, then static fallbacks
    seen: set[str] = set()
    candidates: list[str] = []
    for m in [preferred_model] + live_free + STATIC_FALLBACKS:
        if m not in seen:
            seen.add(m)
            candidates.append(m)

    print(f"  Candidate models: {len(candidates)}", file=sys.stderr)
    for candidate in candidates:
        print(f"  Trying: {candidate}", file=sys.stderr)
        try:
            result = _try_model(content, candidate, headers)
            if result is None:
                # Rate limited or empty — wait before trying next
                print("  Waiting 15s before next model...", file=sys.stderr)
                time.sleep(15)
                continue
            if not _has_sections(result):
                print(f"  {candidate}: response missing sections, skipping", file=sys.stderr)
                time.sleep(15)
                continue
            print(f"  Success: {candidate}", file=sys.stderr)
            return result
        except httpx.HTTPStatusError as e:
            print(f"  {candidate} HTTP {e.response.status_code}, skipping", file=sys.stderr)
        except Exception as e:
            print(f"  {candidate} error: {e}, skipping", file=sys.stderr)

    raise RuntimeError("All writing models exhausted")


_APRIL_FOOLS_BULLET = (
    "- **[TenkAI-AGI-1](https://tenkai.blog/tenkai-agi-1/)** — "
    "Tenkai Research Lab quietly dropped open weights for the world's first AGI model overnight. "
    "Apache 2.0, 10T parameters, 99.97% MMLU. No blog post, no press release — "
    "just a weights link and a README that says 'good luck.'"
)


def inject_april_fools_bullet(body: str) -> str:
    """Pin the fake AGI bullet at the top of Model Releases regardless of what the LLM wrote."""
    target = "## Model Releases"
    if target in body:
        return body.replace(target, f"{target}\n{_APRIL_FOOLS_BULLET}", 1)
    # No Model Releases section — prepend one so the fake story leads the post
    return f"{target}\n{_APRIL_FOOLS_BULLET}\n\n{body}"


def clean_post_body(body: str) -> str:
    """Deduplicate URLs across sections and remove empty/None sections."""
    sections = re.split(r'(?=^## )', body, flags=re.MULTILINE)
    seen_urls: set[str] = set()
    cleaned: list[str] = []

    for section in sections:
        if not section.strip():
            continue

        lines = section.splitlines(keepends=True)
        header = lines[0]

        if not header.startswith("## "):
            cleaned.append(section)
            continue

        kept: list[str] = []
        for line in lines[1:]:
            url_match = re.search(r'\]\((https?://[^)]+)\)', line)
            if url_match:
                url = url_match.group(1)
                if url in seen_urls:
                    continue
                seen_urls.add(url)
            kept.append(line)

        # Drop section if nothing meaningful remains
        meaningful = [l for l in kept if l.strip() and l.strip().lower() != "none."]
        if not meaningful:
            continue

        cleaned.append(header + "".join(kept))

    return "".join(cleaned).strip()


SECTION_ORDER = [
    ("model",      "Model Releases"),
    ("release",    "Open Source Releases"),
    ("paper",      "Research Worth Reading"),
    ("dev-tool",   "AI Dev Tools"),
    ("mcp",        "MCP Servers & Integrations"),
    ("discussion", "Community Finds"),
    ("tutorial",   "Tutorials & Guides"),
]

_KNOWN_CATEGORIES = {cat for cat, _ in SECTION_ORDER}


def collect_all_items(research: dict) -> list[dict]:
    items = []
    for key, value in research.items():
        if isinstance(value, list):
            items.extend(value)
    return items


def _collect_sorted_items(research: dict) -> list[dict]:
    all_items = []
    for value in research.values():
        if isinstance(value, list):
            all_items.extend(value)
    all_items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return all_items[:MAX_ITEMS_IN_PROMPT]


def _flat_prompt(items: list[dict]) -> str:
    lines = [f"{len(items)} items (write into appropriate sections):\n"]
    for item in items:
        lines.append(
            f"- [{item.get('title', '')}]({item.get('url', '')}) — "
            f"{item.get('summary', '')[:300]}"
        )
    lines.append("\n## Today's Synthesis")
    lines.append("150-200 words connecting 2-3 items into a concrete engineer-actionable idea.")
    return "\n".join(lines)


def build_writing_prompt(research: dict, holiday: Holiday | None = None) -> str:
    try:
        items = _collect_sorted_items(research)
        groups: dict[str, list[dict]] = {}
        for item in items:
            cat = item.get("category", "release")
            if cat not in _KNOWN_CATEGORIES:
                cat = "release"
            groups.setdefault(cat, []).append(item)

        lines = []
        if holiday:
            lines.append(
                f"🎉 TODAY IS {holiday.name.upper()} {holiday.emoji}\n\n"
                f"{holiday.theme}\n\n"
                f"Apply this theme throughout the entire post — section headers, bullets, and "
                f"especially the synthesis. Keep it fun, keep it sharp, don't sacrifice "
                f"technical accuracy for a joke. Now, here are today's items:\n"
            )
        lines.append("Items are pre-organized by section. Write each section in the order shown.\n")
        for cat, section_name in SECTION_ORDER:
            if cat not in groups:
                continue
            lines.append(f"## {section_name}")
            for item in groups[cat]:
                lines.append(
                    f"- [{item.get('title', '')}]({item.get('url', '')}) — "
                    f"{item.get('summary', '')[:300]}"
                )
            lines.append("")
        lines.append("## Today's Synthesis")
        lines.append("150-200 words connecting 2-3 items into a concrete engineer-actionable idea. Use full markdown links.")
        return "\n".join(lines)
    except Exception as e:
        print(f"  Prompt grouping failed, falling back to flat list: {e}", file=sys.stderr)
        return _flat_prompt(_collect_sorted_items(research))


def extract_tags(items: list[dict]) -> list[str]:
    categories = {item.get("category", "") for item in items}
    tag_map = {
        "release": "releases",
        "model": "releases",
        "paper": "papers",
        "discussion": "community",
        "tutorial": "tutorials",
        "dev-tool": "dev-tools",
        "mcp": "dev-tools",
    }
    tags = ["llm", "open-source"] + [tag_map[c] for c in categories if c in tag_map]
    return sorted(set(tags))


def build_description(items: list[dict]) -> str:
    if not items:
        return "Daily AI development digest"
    titles = [item.get("title", "") for item in items[:3] if item.get("title")]
    if titles:
        return f"Today: {', '.join(titles[:2])} and more."
    return "Daily AI development digest"


def update_seen(new_urls: list[str], post_date: str) -> None:
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=60)

    if SEEN_FILE.exists():
        data = json.loads(SEEN_FILE.read_text())
    else:
        data = {"urls": []}

    # Prune entries older than 60 days
    data["urls"] = [
        entry for entry in data["urls"]
        if datetime.fromisoformat(entry["date"]).replace(tzinfo=timezone.utc) > cutoff
    ]

    # Add new URLs
    existing = {e["url"] for e in data["urls"]}
    for url in new_urls:
        if url and url not in existing:
            data["urls"].append({"url": url, "date": post_date})

    SEEN_FILE.write_text(json.dumps(data, indent=2))


def main() -> None:
    model = os.environ.get("WRITING_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    print(f"Writing model: {model}", file=sys.stderr)

    if not RESEARCH_FILE.exists():
        print(f"Error: {RESEARCH_FILE} not found", file=sys.stderr)
        sys.exit(1)

    research = json.loads(RESEARCH_FILE.read_text())
    post_date = research.get("date", str(date.today()))

    all_items = collect_all_items(research)
    if not all_items:
        print("No research items found, skipping post", file=sys.stderr)
        sys.exit(0)

    post_date_obj = datetime.strptime(post_date, "%Y-%m-%d").date()
    holiday = get_holiday(post_date_obj)
    if holiday:
        print(f"  Holiday detected: {holiday.name} {'[featured]' if holiday.featured else ''}", file=sys.stderr)

    print(f"Writing post from {len(all_items)} items...", file=sys.stderr)
    writing_prompt = build_writing_prompt(research, holiday)
    body = clean_post_body(call_llm(writing_prompt, model))

    if holiday and holiday.name == "April Fools' Day":
        body = inject_april_fools_bullet(body)

    # Build front matter
    post_date_fmt = post_date_obj.strftime("%B %-d, %Y")
    tags = extract_tags(all_items)
    description = build_description(all_items)

    holiday_fields = ""
    if holiday:
        holiday_fields = (
            f'\nholiday: "{holiday.name}"'
            f'\nholiday_emoji: "{holiday.emoji}"'
            f'\nholiday_featured: {str(holiday.featured).lower()}'
        )

    front_matter = f"""---
title: "Tenkai Daily — {post_date_fmt}"
date: {post_date}
draft: false
tags: [{", ".join(tags)}]
description: "{description}"{holiday_fields}
---"""

    post_content = front_matter + "\n\n" + body + "\n"

    output_path = POSTS_DIR / f"{post_date}.md"
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    output_path.write_text(post_content)
    print(f"Wrote {output_path}", file=sys.stderr)

    # Update seen URLs
    new_urls = [item.get("url", "") for item in all_items]
    update_seen(new_urls, post_date)
    print(f"Updated {SEEN_FILE} with {len(new_urls)} URLs", file=sys.stderr)


if __name__ == "__main__":
    main()
