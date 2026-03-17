---
title: "MCP Plugin"
_build:
  list: never
---

**tenkai-mcp** is an [MCP server](https://modelcontextprotocol.io) that lets your coding assistant search Tenkai Daily — find open-source releases, papers, and tools directly from Claude Code, Cursor, Windsurf, and more.

## Install

Run the interactive installer:

```
npx tenkai-mcp install
```

It detects which coding assistants you have installed and patches their config automatically. Restart your assistant to activate.

## Or use a prompt

Paste this into your coding assistant and it will handle the install:

```
Please install the tenkai-mcp MCP server for me.
Run `npx tenkai-mcp install` and follow the interactive prompts
to configure it for whichever coding assistants I have installed.
```

## Available tools

| Tool | Description |
|------|-------------|
| `search_posts` | Search by keyword — finds releases, papers, and tutorials |
| `get_recent_posts` | Latest N daily posts |
| `list_tags` | All topic tags in the index |

## Example prompts

- *"Search tenkai for recent RAG tools"*
- *"What vector database releases came out this week on tenkai?"*
- *"Find tenkai posts tagged open-source from this month"*

## Manual config

If you prefer to configure manually, add this to your client's MCP settings:

```json
{
  "mcpServers": {
    "tenkai": {
      "command": "npx",
      "args": ["-y", "tenkai-mcp"]
    }
  }
}
```

Config file locations:

| Client | Path |
|--------|------|
| Claude Code (user) | `~/.claude/mcp.json` |
| Claude Code (project) | `.mcp.json` |
| Claude Desktop (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Cursor | `~/.cursor/mcp.json` |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` |
