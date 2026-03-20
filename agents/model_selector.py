#!/usr/bin/env python3
"""Selects the best available free models from OpenRouter for research and writing tasks."""

import json
import os
import re
import sys

import httpx

FALLBACK_MODEL = "meta-llama/llama-3.3-70b-instruct:free"

WRITING_QUALITY_TIERS = [
    "gemini-2",
    "deepseek-r1",
    "llama-3.3-70b",
    "llama-3.1-70b",
    "qwen",
    "mistral-large",
]


def fetch_free_models() -> list[dict]:
    try:
        response = httpx.get(
            "https://openrouter.ai/api/v1/models",
            timeout=15,
            headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
        )
        response.raise_for_status()
        models = response.json().get("data", [])
        return [
            m for m in models
            if str(m.get("pricing", {}).get("prompt", "1")) == "0"
        ]
    except Exception as e:
        print(f"Warning: failed to fetch models: {e}", file=sys.stderr)
        return []


def pick_research_model(free_models: list[dict]) -> str:
    """Largest context window for holding many source excerpts."""
    if not free_models:
        return FALLBACK_MODEL
    ranked = sorted(
        free_models,
        key=lambda m: m.get("context_length", 0),
        reverse=True,
    )
    return ranked[0]["id"]


def parse_param_count(model_id: str) -> int:
    """Extract parameter count (in billions) from a model ID string.

    Looks for patterns like '70b', '27b', '235b'. Returns the largest match
    found, or 0 if none. Used to break ties within a quality tier.
    """
    matches = re.findall(r'(\d+)b(?![a-z])', model_id.lower())
    return max((int(n) for n in matches), default=0)


def pick_writing_model(free_models: list[dict]) -> str:
    """Best quality tier for coherent prose generation, larger models preferred."""
    if not free_models:
        return FALLBACK_MODEL

    for tier_keyword in WRITING_QUALITY_TIERS:
        matches = [m for m in free_models if tier_keyword in m["id"].lower()]
        if matches:
            return max(matches, key=lambda m: parse_param_count(m["id"]))["id"]

    # Fall back to largest context if no tier match
    return pick_research_model(free_models)


def main() -> None:
    free_models = fetch_free_models()

    if not free_models:
        print(f"Warning: using fallback models", file=sys.stderr)
        research_model = FALLBACK_MODEL
        writing_model = FALLBACK_MODEL
    else:
        research_model = pick_research_model(free_models)
        writing_model = pick_writing_model(free_models)

    print(f"Research model: {research_model}", file=sys.stderr)
    print(f"Writing model:  {writing_model}", file=sys.stderr)

    # Write to GitHub Actions env file if available, else print for eval
    env_file = os.environ.get("GITHUB_ENV")
    if env_file:
        with open(env_file, "a") as f:
            f.write(f"RESEARCH_MODEL={research_model}\n")
            f.write(f"WRITING_MODEL={writing_model}\n")
    else:
        print(f"export RESEARCH_MODEL='{research_model}'")
        print(f"export WRITING_MODEL='{writing_model}'")


if __name__ == "__main__":
    main()
