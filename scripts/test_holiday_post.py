#!/usr/bin/env python3
"""
Locally test holiday post writing with dummy research data.

Usage:
    python scripts/test_holiday_post.py                    # pick from list
    python scripts/test_holiday_post.py --date 2026-10-31  # specific date
    python scripts/test_holiday_post.py --list             # show all holidays
"""

import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Allow direct imports from agents/
sys.path.insert(0, str(Path(__file__).parent.parent / "agents"))

from holidays import get_holiday, Holiday
from model_selector import fetch_free_models, pick_writing_model
from writing_agent import (
    build_writing_prompt,
    call_llm,
    clean_post_body,
    inject_april_fools_bullet,
    extract_tags,
    build_description,
)

# ── Dummy research items ─────────────────────────────────────────────────────
# Generic, realistic AI news items. The holiday theming overlays on top of
# whatever content is here, so these don't need to be holiday-specific.

DUMMY_RESEARCH = {
    "source_hf": [
        {
            "title": "Llama-4-Scout-17B-16E",
            "url": "https://huggingface.co/meta-llama/Llama-4-Scout-17B-16E",
            "summary": (
                "Meta releases a 17B Mixture-of-Experts model with 16 experts, "
                "strong on instruction following and tool use. Beats Llama-3.1-70B "
                "on several benchmarks at a fraction of the active parameter count. "
                "Apache 2.0 license, fits on a single A100."
            ),
            "category": "model",
            "relevance_score": 9,
        },
        {
            "title": "Qwen3-8B-Instruct",
            "url": "https://huggingface.co/Qwen/Qwen3-8B-Instruct",
            "summary": (
                "Alibaba's latest 8B model with improved reasoning and 128k context. "
                "Strong on math and coding benchmarks. Apache 2.0. Notable: "
                "outperforms several 70B-class models on GSM8K."
            ),
            "category": "model",
            "relevance_score": 8,
        },
    ],
    "source_arxiv": [
        {
            "title": "SpecDec++: Accelerating Speculative Decoding via Adaptive Candidate Length",
            "url": "https://arxiv.org/abs/2405.19715",
            "summary": (
                "Proposes adaptive candidate length selection for speculative decoding, "
                "achieving up to 2.8x speedup over standard autoregressive decoding "
                "without quality loss. Works with any draft model. Practical for "
                "production inference pipelines."
            ),
            "category": "paper",
            "relevance_score": 8,
        },
        {
            "title": "Scaling Laws for Reward Model Overoptimization in RLHF",
            "url": "https://arxiv.org/abs/2406.02900",
            "summary": (
                "Empirical study of reward hacking as a function of KL divergence "
                "from the reference policy. Finds consistent scaling laws across model "
                "sizes. Useful for calibrating RLHF training runs and knowing when "
                "to stop optimizing."
            ),
            "category": "paper",
            "relevance_score": 7,
        },
    ],
    "source_github": [
        {
            "title": "vLLM v0.5.0",
            "url": "https://github.com/vllm-project/vllm",
            "summary": (
                "Major release: adds chunked prefill for better GPU utilization, "
                "multi-LoRA serving without restarts, and 40% improvement on "
                "Time-to-First-Token for long prompts. Apache 2.0."
            ),
            "category": "dev-tool",
            "relevance_score": 9,
        },
        {
            "title": "smolagents 1.0",
            "url": "https://github.com/huggingface/smolagents",
            "summary": (
                "HuggingFace's minimal agent framework hits stable release. "
                "Code-first design: agents write and execute Python rather than "
                "JSON tool calls. Supports any OpenAI-compatible model. "
                "Small API surface by design."
            ),
            "category": "dev-tool",
            "relevance_score": 8,
        },
        {
            "title": "mcp-code-sandbox",
            "url": "https://github.com/e2b-dev/mcp-code-sandbox",
            "summary": (
                "MCP server wrapping E2B's cloud code execution sandbox. "
                "Gives your coding assistant a real Python environment to run "
                "code in, with filesystem access and package installation. "
                "Handles the security boundary you don't want to manage yourself."
            ),
            "category": "mcp",
            "relevance_score": 8,
        },
    ],
    "source_reddit": [
        {
            "title": "Fine-tuning Llama-4 on consumer hardware: what actually works in 2026",
            "url": "https://reddit.com/r/LocalLLaMA/comments/example/",
            "summary": (
                "Detailed community writeup on QLoRA fine-tuning of Llama-4-Scout "
                "on a 24GB GPU. Covers gradient checkpointing settings, batch size "
                "tradeoffs, and eval results. Reproducible setup with linked configs."
            ),
            "category": "discussion",
            "relevance_score": 7,
        },
    ],
}


# ── Holiday listing ──────────────────────────────────────────────────────────

def upcoming_holidays(from_date: date, n: int = 20) -> list[tuple[date, Holiday]]:
    """Return the next n holidays on or after from_date, searching up to 2 years ahead."""
    results = []
    current = from_date
    end = from_date.replace(year=from_date.year + 2)
    while current <= end and len(results) < n:
        h = get_holiday(current)
        if h:
            results.append((current, h))
        current += timedelta(days=1)
    return results


def all_holidays_this_year(year: int) -> list[tuple[date, Holiday]]:
    results = []
    current = date(year, 1, 1)
    end = date(year, 12, 31)
    while current <= end:
        h = get_holiday(current)
        if h:
            results.append((current, h))
        current += timedelta(days=1)
    return results


def print_holiday_list(holidays: list[tuple[date, Holiday]]) -> None:
    print()
    for i, (d, h) in enumerate(holidays):
        star = "★" if h.featured else " "
        today_marker = " ← today" if d == date.today() else ""
        print(f"  {i+1:2}.  {star} {d.strftime('%b %d')}  {h.emoji}  {h.name}{today_marker}")
    print()
    print("  ★ = rare/featured holiday (elaborate banner + heavier theming)")
    print()


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Test holiday post writing locally.")
    parser.add_argument("--date", help="Date to test (YYYY-MM-DD). Must fall on a holiday.")
    parser.add_argument("--list", action="store_true", help="List all holidays this year and exit.")
    args = parser.parse_args()

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("Error: OPENROUTER_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    # --list mode
    if args.list:
        holidays = all_holidays_this_year(date.today().year)
        print(f"\nAll holidays in {date.today().year}:")
        print_holiday_list(holidays)
        return

    # Resolve the target date and holiday
    if args.date:
        try:
            target = date.fromisoformat(args.date)
        except ValueError:
            print(f"Error: invalid date '{args.date}'. Use YYYY-MM-DD.", file=sys.stderr)
            sys.exit(1)
        holiday = get_holiday(target)
        if holiday is None:
            print(f"Error: {target} is not a recognized holiday.", file=sys.stderr)
            print("Run with --list to see all holidays, or try a different date.")
            sys.exit(1)
    else:
        # Interactive picker
        upcoming = upcoming_holidays(date.today())
        if not upcoming:
            print("No upcoming holidays found. Try --date with an explicit date.")
            sys.exit(1)
        print("\nUpcoming holidays:")
        print_holiday_list(upcoming)
        try:
            choice = input(f"  Pick a number [1-{len(upcoming)}]: ").strip()
            idx = int(choice) - 1
            if idx < 0 or idx >= len(upcoming):
                raise ValueError
        except (ValueError, EOFError):
            print("Invalid choice. Exiting.")
            sys.exit(1)
        target, holiday = upcoming[idx]

    print(f"\n{'─'*60}")
    print(f"  Holiday : {holiday.emoji}  {holiday.name}")
    print(f"  Date    : {target}")
    print(f"  Tier    : {'★ FEATURED' if holiday.featured else 'regular'}")
    print(f"{'─'*60}\n")

    # Pick the best available free writing model
    print("Fetching available free models from OpenRouter...", flush=True)
    free_models = fetch_free_models()
    model = pick_writing_model(free_models)
    print(f"Selected model: {model}\n")

    # Build the writing prompt with holiday injected
    research = {**DUMMY_RESEARCH, "date": target.isoformat()}
    prompt = build_writing_prompt(research, holiday)

    print(f"Calling {model}...\n", flush=True)
    body = clean_post_body(call_llm(prompt, model))

    if holiday.name == "April Fools' Day":
        body = inject_april_fools_bullet(body)

    # Build frontmatter
    all_items = [item for v in DUMMY_RESEARCH.values() if isinstance(v, list) for item in v]
    tags = extract_tags(all_items)
    description = build_description(all_items)
    holiday_fields = (
        f'\nholiday: "{holiday.name}"'
        f'\nholiday_emoji: "{holiday.emoji}"'
        f'\nholiday_featured: {str(holiday.featured).lower()}'
    )
    post_date_fmt = target.strftime("%B %-d, %Y")
    front_matter = (
        f'---\n'
        f'title: "Tenkai Daily — {post_date_fmt}"\n'
        f'date: {target}\n'
        f'draft: false\n'
        f'tags: [{", ".join(tags)}]\n'
        f'description: "{description}"{holiday_fields}\n'
        f'---'
    )
    post = front_matter + "\n\n" + body + "\n"

    # Write to a temp file (never touches content/posts/)
    out = Path(f"/tmp/holiday-test-{target}.md")
    out.write_text(post)

    print(f"{'─'*60}")
    print(post)
    print(f"{'─'*60}")
    print(f"\nAlso written to: {out}")
    print(f"Preview with: hugo server (then copy to content/posts/ temporarily)\n")


if __name__ == "__main__":
    main()
