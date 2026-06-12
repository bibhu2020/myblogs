import { resolve, dirname } from 'path';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

dotenv.config({ path: resolve(dirname(fileURLToPath(import.meta.url)), '../../.env') });

const MCP_URL = process.env.MCP_URL || 'https://mishrabp-myblogs.hf.space/api/mcp';
const MCP_KEY = process.env.MCP_API_KEY || '';

let reqId = 1;

async function mcpRequest(method, params) {
  const body = { jsonrpc: '2.0', id: reqId++, method };
  if (params && Object.keys(params).length) body.params = params;

  const headers = { 'Content-Type': 'application/json' };
  if (MCP_KEY) headers['Authorization'] = `Bearer ${MCP_KEY}`;

  const res = await fetch(MCP_URL, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`MCP HTTP ${res.status}: ${text.slice(0, 300)}`);
  }

  const data = await res.json();
  if (data.error) throw new Error(`MCP error [${data.error.code}]: ${data.error.message}`);
  return data.result;
}

export async function mcpInit() {
  await mcpRequest('initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'meridian-ai-agent', version: '1.0.0' },
  });
}

export async function mcpCall(toolName, args) {
  const result = await mcpRequest('tools/call', { name: toolName, arguments: args });

  if (result?.isError) {
    const msg = result.content?.[0]?.text || 'Unknown tool error';
    throw new Error(`Tool "${toolName}" failed: ${msg}`);
  }

  const text = result?.content?.[0]?.text;
  if (text === undefined) throw new Error(`Tool "${toolName}" returned no content`);

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}
