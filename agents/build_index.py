"""Build semantic search index from all posts.

Outputs static/search-index.json — served by the static site for client-side
semantic search and loadable by Python agents for RAG retrieval.

Model: BAAI/bge-small-en-v1.5 (384-dim, ONNX via fastembed)
Browser counterpart: Xenova/bge-small-en-v1.5 (same weights, same vector space)
"""
import json
import re
from pathlib import Path

from fastembed import TextEmbedding

POSTS_DIR = Path("content/posts")
INDEX_PATH = Path("static/search-index.json")
MODEL = "BAAI/bge-small-en-v1.5"


def parse_post(path: Path) -> dict | None:
    text = path.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    front, body = parts[1], parts[2].strip()

    def field(key):
        m = re.search(rf'^{key}:\s*"?(.+?)"?\s*$', front, re.MULTILINE)
        return m.group(1) if m else ""

    title, date = field("title"), field("date")
    if not title or not date:
        return None

    tags_m = re.search(r'^tags:\s*\[(.+?)\]', front, re.MULTILINE)
    tags = [t.strip().strip('"') for t in tags_m.group(1).split(",")] if tags_m else []

    # Strip markdown for search and display
    stripped = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', body)
    stripped = re.sub(r'[#*`>]', '', stripped).strip()

    return {
        "title": title,
        "date": date,
        "url": f"/posts/{path.stem}/",
        "tags": tags,
        "description": field("description"),
        "snippet": stripped[:300],
        "body": stripped,
        "raw": body,
    }


def main():
    posts = [p for path in sorted(POSTS_DIR.glob("*.md")) if (p := parse_post(path))]
    print(f"Indexing {len(posts)} posts with {MODEL}...")

    model = TextEmbedding(MODEL)
    # Embed title + description + full body for best retrieval quality
    texts = [f"{p['title']}. {p['description']} {p['body']}" for p in posts]
    embeddings = list(model.embed(texts))

    index = [
        {
            "title": post["title"],
            "date": post["date"],
            "url": post["url"],
            "tags": post["tags"],
            "description": post["description"],
            "snippet": post["snippet"],
            "body": post["body"],
            # Round to 5 decimal places — negligible quality loss, ~40% smaller JSON
            "embedding": [round(float(x), 5) for x in emb],
        }
        for post, emb in zip(posts, embeddings)
    ]

    INDEX_PATH.write_text(json.dumps(index, separators=(",", ":")))
    size_kb = INDEX_PATH.stat().st_size // 1024
    print(f"Wrote {INDEX_PATH} ({size_kb} KB, {len(index)} posts)")


if __name__ == "__main__":
    main()
