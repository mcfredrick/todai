#!/usr/bin/env node
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { z } from 'zod';
import { pipeline } from '@huggingface/transformers';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { createInterface } from 'readline';
import { homedir } from 'os';
import { join, dirname } from 'path';

const INDEX_URL = 'https://mcfredrick.github.io/tenkai/search-index.json';
const BASE_URL = 'https://mcfredrick.github.io/tenkai';

// ─── Installer ───────────────────────────────────────────────────────────────

const MCP_ENTRY = {
  command: 'npx',
  args: ['-y', 'tenkai-mcp'],
};

const TARGETS = {
  'Claude Code (user-level, all projects)': join(homedir(), '.claude', 'mcp.json'),
  'Claude Code (project-level, this directory)': join(process.cwd(), '.mcp.json'),
  'Claude Desktop (macOS)': join(homedir(), 'Library', 'Application Support', 'Claude', 'claude_desktop_config.json'),
  'Cursor': join(homedir(), '.cursor', 'mcp.json'),
  'Windsurf': join(homedir(), '.codeium', 'windsurf', 'mcp_config.json'),
};

function readJson(path) {
  if (!existsSync(path)) return {};
  try { return JSON.parse(readFileSync(path, 'utf8')); } catch { return {}; }
}

function writeJson(path, data) {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(data, null, 2) + '\n', 'utf8');
}

function installTo(configPath) {
  const config = readJson(configPath);
  config.mcpServers ??= {};
  if (config.mcpServers.tenkai) {
    console.log('  ✓ tenkai-mcp already configured — updating entry');
  }
  config.mcpServers.tenkai = MCP_ENTRY;
  writeJson(configPath, config);
  console.log(`  ✓ Written to ${configPath}`);
}

async function runInstaller() {
  console.log('\ntenkai-mcp installer\n');
  console.log('Where would you like to install?\n');

  const entries = Object.entries(TARGETS);
  entries.forEach(([label], i) => console.log(`  ${i + 1}) ${label}`));
  console.log(`  ${entries.length + 1}) All of the above\n`);

  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const answer = await new Promise(resolve => rl.question('Choice: ', resolve));
  rl.close();

  const choice = parseInt(answer.trim(), 10);
  if (isNaN(choice) || choice < 1 || choice > entries.length + 1) {
    console.error('Invalid choice.');
    process.exit(1);
  }

  const toInstall = choice === entries.length + 1 ? entries : [entries[choice - 1]];
  console.log();
  for (const [label, path] of toInstall) {
    console.log(`Installing for ${label}…`);
    installTo(path);
  }

  console.log('\nDone! Restart your coding assistant to activate tenkai-mcp.\n');
  console.log('Try asking: "Search tenkai for recent RAG tools" or "What open-source LLM releases came out this week?"\n');
}

// ─── MCP Server ──────────────────────────────────────────────────────────────

let cachedIndex = null;
let cachedEmbedder = null;

async function loadIndex() {
  if (cachedIndex) return cachedIndex;
  const res = await fetch(INDEX_URL);
  if (!res.ok) throw new Error(`Failed to fetch search index: ${res.status}`);
  cachedIndex = await res.json();
  return cachedIndex;
}

async function getEmbedder() {
  if (!cachedEmbedder) {
    cachedEmbedder = await pipeline('feature-extraction', 'Xenova/bge-small-en-v1.5', { dtype: 'fp32' });
  }
  return cachedEmbedder;
}

// Embeddings are L2-normalized by build_index.py, so dot product = cosine similarity
function cosineSim(a, b) {
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  return dot;
}

function keywordScore(post, terms) {
  const haystack = [post.title, post.description, post.body ?? post.snippet, ...(post.tags ?? [])].join(' ').toLowerCase();
  return terms.filter(t => haystack.includes(t)).length / terms.length;
}

async function hybridSearch(posts, query, limit) {
  const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
  const embedder = await getEmbedder();
  const output = await embedder(query, { pooling: 'mean', normalize: true });
  const queryVec = Array.from(output.data);

  return posts
    .filter(p => p.embedding)
    .map(p => ({
      post: p,
      score: cosineSim(queryVec, p.embedding) + 0.3 * keywordScore(p, terms),
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit)
    .map(({ post }) => formatPost(post));
}

function keywordSearch(posts, terms, limit) {
  return posts
    .map(p => ({ post: p, score: keywordScore(p, terms) }))
    .filter(({ score }) => score > 0)
    .sort((a, b) => b.score - a.score || b.post.date.localeCompare(a.post.date))
    .slice(0, limit)
    .map(({ post }) => formatPost(post));
}

function formatPost(post, { snippet = true } = {}) {
  const lines = [
    `**${post.title}** (${post.date})`,
    post.description,
    `URL: ${BASE_URL}${post.url}`,
    `Tags: ${(post.tags ?? []).join(', ')}`,
  ];
  if (snippet && post.snippet) lines.push('', post.snippet);
  return lines.join('\n');
}

async function runServer() {
  const server = new McpServer({ name: 'tenkai-mcp', version: '1.0.0' });

  server.tool(
    'search_posts',
    'Search Tenkai Daily AI news for open-source releases, papers, tools, and tutorials. Returns matching posts with descriptions and links.',
    {
      query: z.string().describe('Keywords to search for (e.g. "RAG vector database", "fine-tuning llama")'),
      limit: z.number().int().min(1).max(20).optional().default(5).describe('Max results to return (default 5)'),
    },
    async ({ query, limit }) => {
      const posts = await loadIndex();
      let results;
      try {
        results = await hybridSearch(posts, query, limit);
      } catch {
        // Fall back to keyword-only if model unavailable
        const terms = query.toLowerCase().split(/\s+/).filter(Boolean);
        results = keywordSearch(posts, terms, limit);
      }

      const text = results.length
        ? results.join('\n\n---\n\n')
        : `No posts found for "${query}". Try broader terms or use list_tags to see available topics.`;

      return { content: [{ type: 'text', text }] };
    }
  );

  server.tool(
    'get_recent_posts',
    'Get the most recent Tenkai Daily posts to see what AI tools and releases came out lately.',
    {
      limit: z.number().int().min(1).max(20).optional().default(5).describe('Number of posts to return (default 5)'),
    },
    async ({ limit }) => {
      const posts = await loadIndex();
      const recent = [...posts]
        .sort((a, b) => b.date.localeCompare(a.date))
        .slice(0, limit)
        .map(p => formatPost(p, { snippet: false }));

      return { content: [{ type: 'text', text: recent.join('\n\n') }] };
    }
  );

  server.tool(
    'list_tags',
    'List all topic tags available in the Tenkai Daily index. Useful for discovering what subject areas are covered.',
    {},
    async () => {
      const posts = await loadIndex();
      const tags = [...new Set(posts.flatMap(p => p.tags ?? []))].sort();
      return { content: [{ type: 'text', text: tags.join(', ') }] };
    }
  );

  const transport = new StdioServerTransport();
  await server.connect(transport);
}

// ─── Entry point ─────────────────────────────────────────────────────────────

if (process.argv[2] === 'install') {
  runInstaller().catch(err => { console.error(err.message); process.exit(1); });
} else {
  runServer().catch(err => { console.error(err.message); process.exit(1); });
}
