#!/usr/bin/env python3
"""Synthesizes research.json into a Hugo markdown post."""

import json
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import time

import httpx

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
- Write like you're texting a colleague who will immediately call you out if you're being boring or vague

Content rules:
- Each bullet: **[Name](url)** — 1-2 sentences. What it is, why an engineer might care (or why they might not)
- Synthesis section: connect 2-3 of today's items into something actually useful. Be specific — vague "synergies" are a war crime
- Only emit sections where you have real content
- No closing remarks, sign-offs, or "that's a wrap!"

Output ONLY the markdown body (no front matter). Structure:

## Open Source Releases
- **[Name](url)** — summary.

## Research Worth Reading
- **[Title](url)** — summary.

## AI Dev Tools
- **[Name](url)** — summary.

## Community Finds
- **[Topic](url)** — summary.

## Tutorials & Guides
- **[Title](url)** — summary.

## Today's Synthesis
150-200 word paragraph connecting 2-3 of today's items into a concrete, engineer-actionable idea. Make it interesting."""


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
    """Return text on success, None on 429, raise on other errors."""
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
    return r.json()["choices"][0]["message"]["content"].strip()


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
            if result is not None:
                print(f"  Success: {candidate}", file=sys.stderr)
                return result
            # Rate limited — wait before trying next
            print("  Waiting 15s before next model...", file=sys.stderr)
            time.sleep(15)
        except httpx.HTTPStatusError as e:
            print(f"  {candidate} HTTP {e.response.status_code}, skipping", file=sys.stderr)
        except Exception as e:
            print(f"  {candidate} error: {e}, skipping", file=sys.stderr)

    raise RuntimeError("All writing models exhausted")


def collect_all_items(research: dict) -> list[dict]:
    items = []
    for key, value in research.items():
        if isinstance(value, list):
            items.extend(value)
    return items


def build_writing_prompt(research: dict) -> str:
    # Collect all items, sort by relevance, cap to MAX_ITEMS_IN_PROMPT
    all_items = []
    for source, items in research.items():
        if isinstance(items, list):
            for item in items:
                all_items.append((source, item))

    all_items.sort(key=lambda x: x[1].get("relevance_score", 0), reverse=True)
    top_items = all_items[:MAX_ITEMS_IN_PROMPT]

    lines = [f"Top {len(top_items)} items by relevance:\n"]
    for source, item in top_items:
        lines.append(
            f"- [{item.get('title', '')}]({item.get('url', '')})\n"
            f"  Source: {source} | Category: {item.get('category', 'unknown')} | "
            f"Relevance: {item.get('relevance_score', 0)}/10\n"
            f"  Summary: {item.get('summary', '')[:300]}"
        )
    return "\n".join(lines)


def extract_tags(items: list[dict]) -> list[str]:
    categories = {item.get("category", "") for item in items}
    tag_map = {
        "release": "releases",
        "paper": "papers",
        "discussion": "community",
        "tutorial": "tutorials",
        "tool": "dev-tools",
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

    print(f"Writing post from {len(all_items)} items...", file=sys.stderr)
    writing_prompt = build_writing_prompt(research)
    body = call_llm(writing_prompt, model)

    # Build front matter
    post_date_fmt = datetime.strptime(post_date, "%Y-%m-%d").strftime("%B %-d, %Y")
    tags = extract_tags(all_items)
    description = build_description(all_items)

    front_matter = f"""---
title: "Tenkai Daily — {post_date_fmt}"
date: {post_date}
draft: false
tags: [{", ".join(tags)}]
description: "{description}"
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
