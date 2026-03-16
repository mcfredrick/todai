/* Semantic search — loads BAAI/bge-small-en-v1.5 via transformers.js (ONNX).
   Index is pre-computed by agents/build_index.py with the same model.
   Both sides produce L2-normalized embeddings, so cosine sim = dot product. */

let index = null;
let embedder = null;

function dot(a, b) {
  let s = 0;
  for (let i = 0; i < a.length; i++) s += a[i] * b[i];
  return s;
}

async function loadResources(statusEl) {
  if (index && embedder) return;

  statusEl.textContent = "Loading search index\u2026";
  const [idx, { pipeline }] = await Promise.all([
    fetch("/search-index.json").then((r) => {
      if (!r.ok) throw new Error(`search-index.json fetch failed: ${r.status} ${r.url}`);
      return r.json();
    }),
    import(
      "https://cdn.jsdelivr.net/npm/@xenova/transformers@2/dist/transformers.min.js"
    ),
  ]);
  index = idx;

  statusEl.textContent =
    "Loading model (first visit ~7 MB, cached after)\u2026";
  embedder = await pipeline("feature-extraction", "Xenova/bge-small-en-v1.5", {
    quantized: true,
  });

  statusEl.textContent = "";
}

async function search(query, statusEl) {
  await loadResources(statusEl);
  statusEl.textContent = "Searching\u2026";

  const out = await embedder(query, { pooling: "mean", normalize: true });
  const qEmb = Array.from(out.data);

  return index
    .map((post) => ({ ...post, score: dot(qEmb, post.embedding) }))
    .sort((a, b) => b.score - a.score)
    .slice(0, 10);
}

function renderResults(results, container) {
  if (!results.length) {
    container.innerHTML = '<p class="search-empty">No results found.</p>';
    return;
  }
  container.innerHTML = results
    .map(
      (r) => `
    <article class="search-result">
      <h3><a href="${r.url}">${r.title}</a></h3>
      <div class="search-meta">
        <span class="search-date">${r.date}</span>
        ${r.tags
          .map(
            (t) =>
              `<a href="/tags/${t.toLowerCase().replace(/\s+/g, "-")}/" class="tag">${t}</a>`
          )
          .join("")}
      </div>
      <p class="search-snippet">${r.snippet}</p>
    </article>`
    )
    .join("");
}

document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("search-form");
  const input = document.getElementById("search-input");
  const results = document.getElementById("search-results");
  const status = document.getElementById("search-status");
  if (!form) return;

  // Pre-fill from ?q= query string
  const q = new URLSearchParams(window.location.search).get("q");
  if (q) {
    input.value = q;
    runSearch(q);
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const query = input.value.trim();
    if (query) runSearch(query);
  });

  async function runSearch(query) {
    results.innerHTML = "";
    try {
      const hits = await search(query, status);
      status.textContent = `${hits.length} result${hits.length !== 1 ? "s" : ""}`;
      renderResults(hits, results);
    } catch (err) {
      status.textContent = "Search failed — check console.";
      console.error(err);
    }
  }
});
