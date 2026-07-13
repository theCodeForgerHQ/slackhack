import { describe, test, expect, beforeEach } from 'vitest';
import { AnswerLibrary } from '../src/core/library.js';
import { LedgerV2 } from '../src/core/ledgerV2.js';
import { decide } from '../src/core/decide.js';
import { buildMcpServerV2 } from '../src/mcp/serverV2.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';

describe('MCP server v2 — human-gated writes', () => {
  let library: AnswerLibrary;
  let ledgerV2: LedgerV2;

  beforeEach(() => {
    library = AnswerLibrary.inMemory();
    ledgerV2 = LedgerV2.inMemory();
  });

  async function connectedClient(writesEnabled: boolean) {
    const server = buildMcpServerV2(library, {
      identity: 'U_ADMIN',
      visibility: { canSee: async () => true },
      ledgerV2,
      writesEnabled,
    });
    const [ct, st] = InMemoryTransport.createLinkedPair();
    const client = new Client({ name: 't', version: '0' });
    await Promise.all([server.connect(st), client.connect(ct)]);
    return client;
  }

  test('propose_answer is discoverable but returns writes_disabled when writes are disabled', async () => {
    const client = await connectedClient(false);
    const result = await client.callTool({
      name: 'propose_answer',
      arguments: {
        questionText: 'Do you encrypt data at rest?',
        answerText: 'Yes, AES-256.',
        citations: [{ permalink: 'p/enc', channelId: 'C1', ts: '1' }],
      },
    });
    const text = (result.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    expect(text).toContain('writes_disabled');
    expect(ledgerV2.entries()).toHaveLength(0);
  });

  test('propose_answer creates a pending proposal event but does not approve it', async () => {
    const client = await connectedClient(true);
    const result = await client.callTool({
      name: 'propose_answer',
      arguments: {
        questionText: 'Do you encrypt data at rest?',
        answerText: 'Yes, AES-256.',
        citations: [{ permalink: 'p/enc', channelId: 'C1', ts: '1' }],
      },
    });

    const text = (result.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    expect(text).toContain('pending_human_approval');

    const events = ledgerV2.entries();
    expect(events).toHaveLength(1);
    expect(events[0]?.type).toBe('AnswerProposed');

    // Library must remain empty: agent proposals require human approval.
    expect(library.searchAnswers('encrypt')).toHaveLength(0);
  });

  test('duplicate proposal for same answerId is rejected by decide policy', () => {
    const first = decide([], {
      type: 'Propose',
      answerId: 99,
      questionText: 'Q1',
      answerText: 'A1',
      citations: [],
    });
    expect(first.ok).toBe(true);

    const second = decide(first.events ?? [], {
      type: 'Propose',
      answerId: 99,
      questionText: 'Q1',
      answerText: 'A1',
      citations: [],
    });
    expect(second.ok).toBe(false);
  });
});
