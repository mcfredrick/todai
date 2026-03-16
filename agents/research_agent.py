#!/usr/bin/env python3
"""Fetches sources, calls research LLM to extract items, writes /tmp/research.json."""

import json
import os
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

from sources import ALL_SOURCES

OPENROUTER_API = "https://openrouter.ai/api/v1/chat/completions"
SEEN_FILE = Path(__file__).parent / "seen.json"
OUTPUT_FILE = Path("/tmp/research.json")
BUSINESS_KEYWORDS = {"funding", "valuation", "ipo", "acquisition", "acquires", "merger", "raises", "series a", "series b", "series c"}

SYSTEM_PROMPT = """You are a technical research assistant for AI/ML engineers.

Extract technically relevant items from the provided content. Focus on:
- New open-source releases and framework updates
- Practical research papers with engineering implications
- Developer techniques, tools, and libraries
- Performance benchmarks and optimization findings

Exclude strictly:
- Business news: funding, acquisitions, valuations, IPOs, layoffs
- Marketing announcements without technical substance
- Hype without concrete details

For each item, if multiple URLs point to the same story, pick the most useful/canonical one.

Return ONLY a JSON array. Each element must have exactly these fields:
{
  "title": "concise title",
  "url": "canonical URL",
  "summary": "2-3 sentence technical summary",
  "category": "release|paper|discussion|tutorial",
  "relevance_score": <integer 1-10>
}

Drop items with relevance_score below 7. Return [] if nothing qualifies."""


def load_seen_urls() -> set[str]:
    if not SEEN_FILE.exists():
        return set()
    data = json.loads(SEEN_FILE.read_text())
    return {entry["url"] for entry in data.get("urls", [])}


def call_llm(content: str, model: str, retries: int = 3) -> list[dict]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "temperature": 0.3,
    }
    headers = {
        "Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}",
        "HTTP-Referer": "https://github.com/mcfredrick/tenkai",
        "X-Title": "Tenkai Research Agent",
    }

    for attempt in range(retries):
        try:
            r = httpx.post(OPENROUTER_API, json=payload, headers=headers, timeout=120)
            if r.status_code == 429:
                wait = 2 ** attempt * 5
                print(f"  Rate limited, waiting {wait}s...", file=sys.stderr)
                time.sleep(wait)
                continue
            r.raise_for_status()
            text = r.json()["choices"][0]["message"]["content"].strip()
            # Extract JSON array from response
            start = text.find("[")
            end = text.rfind("]") + 1
            if start == -1 or end == 0:
                return []
            return json.loads(text[start:end])
        except Exception as e:
            print(f"  LLM call failed (attempt {attempt + 1}): {e}", file=sys.stderr)
            if attempt < retries - 1:
                time.sleep(2 ** attempt * 2)

    return []


def is_business_news(item: dict) -> bool:
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    return any(kw in text for kw in BUSINESS_KEYWORDS)


def fetch_all_sources() -> dict[str, list[dict]]:
    raw: dict[str, list[dict]] = {}
    for name, fetcher in ALL_SOURCES.items():
        print(f"Fetching {name}...", file=sys.stderr)
        try:
            raw[name] = fetcher()
            print(f"  {len(raw[name])} items", file=sys.stderr)
        except Exception as e:
            print(f"  Error fetching {name}: {e}", file=sys.stderr)
            raw[name] = []
    return raw


def build_prompt_for_source(name: str, items: list[dict]) -> str:
    lines = [f"Source: {name}", ""]
    for item in items[:30]:  # cap per source to manage token usage
        lines.append(f"Title: {item.get('title', '')}")
        lines.append(f"URL: {item.get('url', '')}")
        lines.append(f"Text: {item.get('text', '')[:400]}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    model = os.environ.get("RESEARCH_MODEL", "meta-llama/llama-3.3-70b-instruct:free")
    print(f"Research model: {model}", file=sys.stderr)

    seen_urls = load_seen_urls()
    print(f"Loaded {len(seen_urls)} seen URLs", file=sys.stderr)

    raw_sources = fetch_all_sources()

    # Process each source through LLM
    results: dict[str, list[dict]] = {"date": str(date.today())}
    for source_name, items in raw_sources.items():
        if not items:
            results[source_name] = []
            continue

        print(f"Processing {source_name} with LLM...", file=sys.stderr)
        prompt = build_prompt_for_source(source_name, items)
        extracted = call_llm(prompt, model)

        # Filter seen URLs and business news
        filtered = [
            item for item in extracted
            if item.get("url") not in seen_urls
            and not is_business_news(item)
        ]
        results[source_name] = filtered
        print(f"  {len(filtered)} items after filtering", file=sys.stderr)

    total = sum(len(v) for v in results.values() if isinstance(v, list))
    print(f"Total research items: {total}", file=sys.stderr)

    OUTPUT_FILE.write_text(json.dumps(results, indent=2))
    print(f"Wrote {OUTPUT_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
