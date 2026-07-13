// Bundled task-tracker MCP server (stdio). Threadwork's approve flow files the
// executed task here via a real MCP tool call - the stand-in for an external
// tracker (swap this server for Jira/Linear/etc. without touching Threadwork).
// Tasks land in data/tracker.json as TASK-<n>.
const fs = require('fs');
const path = require('path');

const FILE = path.join(__dirname, '..', 'data', 'tracker.json');

function load() {
  try {
    return JSON.parse(fs.readFileSync(FILE, 'utf8'));
  } catch {
    return { next_id: 1, tasks: [] };
  }
}

function save(db) {
  fs.mkdirSync(path.dirname(FILE), { recursive: true });
  fs.writeFileSync(FILE, JSON.stringify(db, null, 2));
}

(async () => {
  const { McpServer } = await import('@modelcontextprotocol/sdk/server/mcp.js');
  const { StdioServerTransport } = await import('@modelcontextprotocol/sdk/server/stdio.js');
  const { z } = await import('zod');

  const server = new McpServer({ name: 'threadwork-tracker', version: '1.0.0' });

  server.registerTool(
    'create_task',
    {
      title: 'Create task',
      description: 'File a task in the tracker. Returns the created task id.',
      inputSchema: {
        title: z.string().describe('Short task title'),
        description: z.string().optional().describe('What was done / what is needed'),
        owner: z.string().optional().describe('Owner display name'),
        source: z.string().optional().describe('Permalink to the originating Slack thread'),
      },
    },
    async ({ title, description, owner, source }) => {
      const db = load();
      const id = `TASK-${db.next_id}`;
      db.next_id += 1;
      db.tasks.push({
        id,
        title,
        description: description || '',
        owner: owner || null,
        source: source || null,
        status: 'done',
        created_at: new Date().toISOString(),
      });
      save(db);
      return { content: [{ type: 'text', text: JSON.stringify({ id }) }] };
    }
  );

  server.registerTool(
    'list_tasks',
    { title: 'List tasks', description: 'List all filed tasks.', inputSchema: {} },
    async () => ({ content: [{ type: 'text', text: JSON.stringify(load().tasks) }] })
  );

  await server.connect(new StdioServerTransport());
})();
