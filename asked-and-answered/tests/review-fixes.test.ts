import { describe, test, expect } from 'vitest';
import { DraftingPipeline, type DraftingLlm } from '../src/core/pipeline.js';
import { AnswerLibrary, type VisibilityChecker } from '../src/core/library.js';
import { Ledger } from '../src/core/ledger.js';
import { QueryPlanner, RateBudget, buildSearchQuery, type RtsClient } from '../src/core/planner.js';
import { buildMcpServer } from '../src/mcp/server.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import type { Question } from '../src/core/types.js';

function q(id: string, text: string): Question {
  return { id, text, sourceRef: id };
}

const goodLlm: DraftingLlm = {
  async draft(_q, hits) {
    const snippet = hits[0]?.snippet ?? '';
    return { kind: 'answer', answerText: `Yes — ${snippet}.`, citedPermalinks: [hits[0]?.permalink ?? ''] };
  },
};

describe('CRITICAL-1: grounded drafts re-check requester visibility on cited evidence', () => {
  test('evidence exists and LLM drafts, but requester cannot see the cited channel → needs_sme, no text', async () => {
    const noneVisible: VisibilityChecker = { canSee: async () => false };
    const pipeline = new DraftingPipeline(AnswerLibrary.inMemory(), goodLlm, noneVisible);

    const results = await pipeline.run(
      [q('q1', 'Do you encrypt data at rest?')],
      new Map([
        ['q1', {
          questionId: 'q1',
          searchFailed: false,
          hits: [{ permalink: 'https://s.example/priv', channelId: 'C_PRIVATE', ts: '1.0', snippet: 'AES-256' }],
        }],
      ]),
      'U_OUTSIDER',
    );

    expect(results[0]?.state).toBe('needs_sme');
    expect(results[0]?.reason).toBe('acl_degraded');
    expect(results[0]?.answerText).toBeUndefined();
    expect(JSON.stringify(results)).not.toContain('Drafted from evidence.');
  });
});

describe('CRITICAL-2: MCP server is identity-bound and redacts unverifiable answers', () => {
  async function connectedClient(visibility: VisibilityChecker) {
    const library = AnswerLibrary.inMemory();
    library.saveApproved({
      questionText: 'Where is customer data hosted?',
      answerText: 'SECRET_REGION',
      citations: [{ permalink: 'https://s.example/priv', channelId: 'C_PRIVATE', ts: '1.0' }],
      approvedBy: 'U_SME',
    });
    const server = buildMcpServer(library, { identity: 'U_BOUND', visibility });
    const [ct, st] = InMemoryTransport.createLinkedPair();
    const client = new Client({ name: 't', version: '0' });
    await Promise.all([server.connect(st), client.connect(ct)]);
    return client;
  }

  test('bound identity without visibility gets provenance but REDACTED answer text', async () => {
    const client = await connectedClient({ canSee: async () => false });
    const result = await client.callTool({ name: 'search_answers', arguments: { query: 'customer data hosted' } });
    const text = (result.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    expect(text).not.toContain('SECRET_REGION');
    expect(text).toMatch(/redacted/i);
  });

  test('bound identity with full visibility gets the answer text', async () => {
    const client = await connectedClient({ canSee: async () => true });
    const result = await client.callTool({ name: 'search_answers', arguments: { query: 'customer data hosted' } });
    const text = (result.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    expect(text).toContain('SECRET_REGION');
  });
});

describe('CRITICAL-regression: MCP server fails CLOSED when visibility is unconfigured', () => {
  async function client(opts?: Parameters<typeof buildMcpServer>[1]) {
    const library = AnswerLibrary.inMemory();
    library.saveApproved({
      questionText: 'Where is customer data hosted?',
      answerText: 'SECRET_REGION',
      citations: [{ permalink: 'https://s.example/priv', channelId: 'C_PRIVATE', ts: '1.0' }],
      approvedBy: 'U_SME',
    });
    const server = buildMcpServer(library, opts);
    const [ct, st] = InMemoryTransport.createLinkedPair();
    const c = new Client({ name: 't', version: '0' });
    await Promise.all([server.connect(st), c.connect(ct)]);
    return c;
  }

  test('no options → evidence-backed answer text is redacted (fail closed, not open)', async () => {
    const c = await client();
    const result = await c.callTool({ name: 'search_answers', arguments: { query: 'customer data hosted' } });
    const text = (result.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    expect(text).not.toContain('SECRET_REGION');
    expect(text).toMatch(/redacted/i);
  });

  test('explicit allow-all visibility → answer text is served (opt-in)', async () => {
    const c = await client({ identity: 'U', visibility: { canSee: async () => true } });
    const result = await c.callTool({ name: 'search_answers', arguments: { query: 'customer data hosted' } });
    const text = (result.content as Array<{ type: string; text: string }>)[0]?.text ?? '';
    expect(text).toContain('SECRET_REGION');
  });
});

describe('CRITICAL-3: production Ledger class has no tamper surface', () => {
  test('Ledger exposes no _tamperForTest method', () => {
    const ledger = Ledger.inMemory();
    expect((ledger as unknown as Record<string, unknown>)._tamperForTest).toBeUndefined();
  });
});

describe('HIGH: SME testimony is labeled as testimony, not silently evidence-verified', () => {
  test('answers saved without citations carry provenance kind sme_testimony', async () => {
    const library = AnswerLibrary.inMemory();
    library.saveApproved({
      questionText: 'Do you carry cyber liability insurance?',
      answerText: 'Yes, $5M via Acme.',
      citations: [],
      approvedBy: 'U_SME',
      kind: 'sme_testimony',
    });

    const hit = await library.findVerified(
      'Do you carry cyber liability insurance?',
      'U_ANY',
      { canSee: async () => true },
    );
    expect(hit.status).toBe('verified');
    if (hit.status === 'verified') expect(hit.answer.kind).toBe('sme_testimony');
  });

  test('evidence-kind answers cannot be saved with zero citations', () => {
    const library = AnswerLibrary.inMemory();
    expect(() =>
      library.saveApproved({
        questionText: 'Q?',
        answerText: 'A.',
        citations: [],
        approvedBy: 'U_SME',
        kind: 'evidence',
      }),
    ).toThrow();
  });
});

describe('MEDIUM: planner robustness', () => {
  test('OR-batch drops hits with zero token overlap instead of misfiling them', async () => {
    const rts: RtsClient = {
      async searchContext() {
        return {
          hits: [{ permalink: 'https://s.example/noise', channelId: 'C1', ts: '1.0', snippet: 'xylophone zebra unrelated' }],
        };
      },
    };
    const planner = new QueryPlanner(rts, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    });

    const result = await planner.retrieve(
      [q('q1', 'Do you encrypt data at rest?'), q('q2', 'Is MFA enforced for employees?')],
      { strategy: 'or-batch' },
    );

    expect(result.get('q1')?.hits).toHaveLength(0);
    expect(result.get('q2')?.hits).toHaveLength(0);
  });

  test('all-stopword questions skip the RTS call instead of sending an empty query', async () => {
    const calls: string[] = [];
    const rts: RtsClient = {
      async searchContext(params) {
        calls.push(params.query);
        return { hits: [] };
      },
    };
    const planner = new QueryPlanner(rts, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    });

    const result = await planner.retrieve([q('q1', 'What is it?')], { strategy: 'per-question' });

    expect(calls).toHaveLength(0);
    expect(result.get('q1')?.hits).toHaveLength(0);
    expect(buildSearchQuery('What is it?')).toBe('');
  });
});

describe('MEDIUM: visibility-check failure degrades one question, not the whole run', () => {
  test('library lookup throwing routes that question to needs_sme instead of crashing', async () => {
    const library = AnswerLibrary.inMemory();
    library.saveApproved({
      questionText: 'Do you encrypt data at rest?',
      answerText: 'Yes.',
      citations: [{ permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' }],
      approvedBy: 'U_SME',
    });
    const throwing: VisibilityChecker = {
      canSee: async () => {
        throw new Error('slack timeout');
      },
    };
    const pipeline = new DraftingPipeline(library, goodLlm, throwing);

    const results = await pipeline.run(
      [q('q1', 'Do you encrypt data at rest?')],
      new Map([['q1', { questionId: 'q1', searchFailed: false, hits: [] }]]),
      'U_REQ',
    );

    expect(results[0]?.state).toBe('needs_sme');
    expect(results[0]?.answerText).toBeUndefined();
  });
});
