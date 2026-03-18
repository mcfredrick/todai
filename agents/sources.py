"""Source fetchers for the research agent. Each returns raw content or []."""

import re
import sys
from typing import Any

import feedparser
import httpx

HEADERS = {"User-Agent": "tenkai-bot/1.0 (github.com/mattdlong/tenkai)"}
TIMEOUT = 20

AI_KEYWORDS = re.compile(
    r"\b(llm|gpt|bert|transformer|diffusion|embedding|rag|vector|"
    r"langchain|llamaindex|ollama|hugging.?face|openai|anthropic|"
    r"pytorch|tensorflow|jax|triton|vllm|inference|fine.?tun|"
    r"tokeniz|neural|generative|foundation.model|ai|ml|nlp)\b",
    re.IGNORECASE,
)


def _get(url: str, **kwargs) -> httpx.Response | None:
    try:
        r = httpx.get(url, headers=HEADERS, timeout=TIMEOUT, follow_redirects=True, **kwargs)
        r.raise_for_status()
        return r
    except Exception as e:
        print(f"  fetch failed {url}: {e}", file=sys.stderr)
        return None


def _scrape_github_trending(language: str) -> list[dict]:
    from bs4 import BeautifulSoup

    r = _get(f"https://github.com/trending/{language}?since=daily")
    if not r:
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []
    for article in soup.select("article.Box-row"):
        try:
            name_tag = article.select_one("h2 a")
            if not name_tag:
                continue
            repo_path = name_tag["href"].lstrip("/")
            url = f"https://github.com/{repo_path}"
            desc_tag = article.select_one("p")
            desc = desc_tag.get_text(strip=True) if desc_tag else ""
            results.append({"title": repo_path, "url": url, "text": desc})
        except Exception:
            continue
    return results


def github_trending() -> list[dict]:
    """Scrape GitHub trending Python and TypeScript repos."""
    return _scrape_github_trending("python") + _scrape_github_trending("typescript")


def huggingface_new_models() -> list[dict]:
    """Fetch trending HuggingFace models by likes."""
    r = _get(
        "https://huggingface.co/api/models",
        params={"sort": "likes7d", "direction": -1, "limit": 20},
    )
    if not r:
        return []

    results = []
    for model in r.json():
        model_id = model.get("id", "")
        url = f"https://huggingface.co/{model_id}"
        tags = " ".join(model.get("tags", []))
        results.append({"title": model_id, "url": url, "text": tags})
    return results


def papers_with_code() -> list[dict]:
    """Fetch recent LLM papers from Papers With Code."""
    r = _get(
        "https://paperswithcode.com/api/v1/papers/",
        params={"ordering": "-published", "q": "llm", "items_per_page": 20},
    )
    if not r:
        return []

    results = []
    for paper in r.json().get("results", []):
        results.append({
            "title": paper.get("title", ""),
            "url": paper.get("url_pdf") or paper.get("url_abs", ""),
            "text": paper.get("abstract", ""),
        })
    return results


def arxiv_feeds() -> list[dict]:
    """Fetch recent papers from ArXiv cs.AI, cs.LG, cs.CL."""
    results = []
    for category in ("cs.AI", "cs.LG", "cs.CL"):
        feed = feedparser.parse(f"https://arxiv.org/rss/{category}")
        for entry in feed.entries[:15]:
            results.append({
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "text": entry.get("summary", ""),
            })
    return results


def hacker_news() -> list[dict]:
    """Fetch high-scoring HN threads about AI/LLM."""
    r = _get(
        "https://hn.algolia.com/api/v1/search",
        params={
            "tags": "story",
            "query": "AI LLM",
            "numericFilters": "points>50",
            "hitsPerPage": 20,
        },
    )
    if not r:
        return []

    results = []
    for hit in r.json().get("hits", []):
        results.append({
            "title": hit.get("title", ""),
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "text": f"Points: {hit.get('points', 0)}, Comments: {hit.get('num_comments', 0)}",
        })
    return results


def pypi_updates() -> list[dict]:
    """Fetch recent PyPI package updates filtered by AI keywords."""
    feed = feedparser.parse("https://pypi.org/rss/updates.xml")
    results = []
    for entry in feed.entries[:50]:
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        if AI_KEYWORDS.search(title) or AI_KEYWORDS.search(summary):
            results.append({
                "title": title,
                "url": entry.get("link", ""),
                "text": summary,
            })
    return results


def _hn_search(query: str, min_points: int = 30, limit: int = 15) -> list[dict]:
    r = _get(
        "https://hn.algolia.com/api/v1/search",
        params={
            "tags": "story",
            "query": query,
            "numericFilters": f"points>{min_points}",
            "hitsPerPage": limit,
        },
    )
    if not r:
        return []
    return [
        {
            "title": hit.get("title", ""),
            "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
            "text": f"Points: {hit.get('points', 0)}, Comments: {hit.get('num_comments', 0)}",
        }
        for hit in r.json().get("hits", [])
    ]


def hacker_news_devtools() -> list[dict]:
    """Fetch HN threads about agentic coding assistants and AI dev tools."""
    return _hn_search("claude code cursor windsurf")


def hacker_news_mcp() -> list[dict]:
    """Fetch HN threads about MCP and the model context protocol ecosystem."""
    return _hn_search("MCP model context protocol")


def github_ai_tool_releases() -> list[dict]:
    """Fetch recent releases from key AI dev tool repos via GitHub Atom feeds."""
    repos = [
        "anthropics/claude-code",
        "block/goose",
        "modelcontextprotocol/servers",
        "continuedev/continue",
        "paul-gauthier/aider",
    ]
    results = []
    for repo in repos:
        feed = feedparser.parse(f"https://github.com/{repo}/releases.atom")
        for entry in feed.entries[:3]:
            results.append({
                "title": f"{repo}: {entry.get('title', '')}",
                "url": entry.get("link", ""),
                "text": entry.get("summary", "")[:400],
            })
    return results


ALL_SOURCES: dict[str, Any] = {
    "github_trending": github_trending,
    "huggingface_releases": huggingface_new_models,
    "papers": papers_with_code,
    "arxiv": arxiv_feeds,
    "hn_threads": hacker_news,
    "hn_devtools": hacker_news_devtools,
    "hn_mcp": hacker_news_mcp,
    "github_tool_releases": github_ai_tool_releases,
    "pypi_updates": pypi_updates,
}
