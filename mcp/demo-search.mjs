#!/usr/bin/env node
// Demo helper: calls the MCP server's search tool and pretty-prints results
import { spawn } from 'child_process';

const query = process.argv[2] || 'RAG vector database';

const messages = [
  { jsonrpc: '2.0', id: 1, method: 'initialize', params: { protocolVersion: '2024-11-05', capabilities: {}, clientInfo: { name: 'demo', version: '1.0' } } },
  { jsonrpc: '2.0', id: 2, method: 'tools/call', params: { name: 'search_posts', arguments: { query, limit: 3 } } },
];

const proc = spawn('node', ['index.js'], { cwd: new URL('.', import.meta.url).pathname });

let output = '';
proc.stdout.on('data', d => { output += d.toString(); });

proc.stderr.on('data', () => {});

for (const msg of messages) {
  proc.stdin.write(JSON.stringify(msg) + '\n');
}

setTimeout(() => {
  proc.stdin.end();
  const lines = output.trim().split('\n').filter(Boolean);
  const result = lines.map(l => { try { return JSON.parse(l); } catch { return null; } }).filter(Boolean);
  const toolResult = result.find(r => r.id === 2);
  if (toolResult?.result?.content?.[0]?.text) {
    console.log(toolResult.result.content[0].text);
  }
  proc.kill();
}, 3000);
