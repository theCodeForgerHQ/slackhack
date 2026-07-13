import { describe, test, expect, beforeEach } from 'vitest';
import { buildMcpServer } from '../src/mcp/server.js';
import { AnswerLibrary } from '../src/core/library.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

describe('asked-answered-mcp', () => {
  let library: AnswerLibrary;
  let client: Client;

  beforeEach(async () => {
    library = AnswerLibrary.inMemory();
    library.saveApproved({
      questionText: 'Do you encrypt data at rest?',
      answerText: 'Yes — AES-256 via cloud KMS.',
      citations: [{ permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' }],
      approvedBy: 'U_SME',
    });

    // Explicit allow-all visibility: these tests exercise tool contracts, not
    // the ACL redaction (that lives in review-fixes.test.ts).
    const server = buildMcpServer(library, { identity: 'U_TEST', visibility: { canSee: async () => true } });
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    client = new Client({ name: 'test-client', version: '0.0.1' });
    await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  });

  test('exposes exactly two read-only tools', async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual(['get_answer_provenance', 'search_answers']);
    for (const tool of tools) {
      expect(tool.annotations?.readOnlyHint).toBe(true);
    }
  });

  test('search_answers returns approved answers with provenance for a matching query', async () => {
    const result = await client.callTool({
      name: 'search_answers',
      arguments: { query: 'encrypt data at rest' },
    });

    const text = (result.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    const parsed = JSON.parse(text) as Array<{ questionText: string; answerText: string; approvedBy: string }>;
    expect(parsed).toHaveLength(1);
    expect(parsed[0]?.answerText).toBe('Yes — AES-256 via cloud KMS.');
    expect(parsed[0]?.approvedBy).toBe('U_SME');
  });

  test('search_answers returns an empty list for no match', async () => {
    const result = await client.callTool({
      name: 'search_answers',
      arguments: { query: 'quantum roadmap' },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    expect(JSON.parse(text)).toEqual([]);
  });

  test('get_answer_provenance returns citations and approval record by answer id', async () => {
    const search = await client.callTool({
      name: 'search_answers',
      arguments: { query: 'encrypt data at rest' },
    });
    const searchText = (search.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    const id = (JSON.parse(searchText) as Array<{ id: number }>)[0]?.id;

    const result = await client.callTool({
      name: 'get_answer_provenance',
      arguments: { answerId: id },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    const parsed = JSON.parse(text) as {
      citations: Array<{ permalink: string }>;
      approvedBy: string;
      approvedAt: string;
    };
    expect(parsed.citations[0]?.permalink).toBe('https://s.example/p1');
    expect(parsed.approvedBy).toBe('U_SME');
    expect(parsed.approvedAt).toMatch(/^\d{4}-/);
  });

  test('get_answer_provenance for an unknown id returns a not-found error result', async () => {
    const result = await client.callTool({
      name: 'get_answer_provenance',
      arguments: { answerId: 99999 },
    });
    expect(result.isError).toBe(true);
  });
});
