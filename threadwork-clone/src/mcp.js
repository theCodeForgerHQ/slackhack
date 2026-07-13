// MCP client (qualifying tech #3). Connects over stdio to the bundled
// task-tracker MCP server; the approve flow files the executed task through it.
// Degrades silently: if the server can't start, FEATURE_MCP stays false.
const path = require('path');

let client = null;

async function connect() {
  try {
    const { Client } = await import('@modelcontextprotocol/sdk/client/index.js');
    const { StdioClientTransport } = await import('@modelcontextprotocol/sdk/client/stdio.js');
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [path.join(__dirname, '..', 'scripts', 'mcp-tracker-server.js')],
    });
    const c = new Client({ name: 'threadwork', version: '1.0.0' });
    await c.connect(transport);
    client = c;
    const tools = await c.listTools();
    console.log(`[mcp] connected to threadwork-tracker, tools: ${tools.tools.map((t) => t.name).join(', ')}`);
  } catch (err) {
    client = null;
    console.warn('[mcp] unavailable (approve flow will skip filing):', err.message);
  }
  return !!client;
}

const available = () => !!client;

// Returns the created task id (e.g. "TASK-3") or null - never throws.
async function fileTask({ title, description, owner, source }) {
  if (!client) return null;
  try {
    const res = await client.callTool({
      name: 'create_task',
      arguments: { title, description, owner: owner || undefined, source: source || undefined },
    });
    const text = res.content && res.content[0] && res.content[0].text;
    return (JSON.parse(text) || {}).id || null;
  } catch (err) {
    console.warn('[mcp] create_task failed:', err.message);
    return null;
  }
}

module.exports = { connect, available, fileTask };
