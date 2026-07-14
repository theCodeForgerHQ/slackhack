import { describe, test, expect } from 'vitest';
import {
  RateBudget,
  buildSearchQuery,
  QueryPlanner,
  type RtsClient,
  type RtsSearchParams,
  type RtsHit,
} from '../src/core/planner.js';
import type { Question } from '../src/core/types.js';

function q(id: string, text: string): Question {
  return { id, text, sourceRef: id };
}

function fakeRts(
  responder: (params: RtsSearchParams) => RtsHit[] | Error,
): { client: RtsClient; calls: RtsSearchParams[] } {
  const calls: RtsSearchParams[] = [];
  return {
    calls,
    client: {
      async searchContext(params) {
        calls.push(params);
        const out = responder(params);
        if (out instanceof Error) throw out;
        return { hits: out };
      },
    },
  };
}

describe('RateBudget', () => {
  test('allows 10 calls immediately, delays the 11th to the window edge', () => {
    let now = 0;
    const budget = new RateBudget({ maxPerWindow: 10, windowMs: 60_000, now: () => now });

    for (let i = 0; i < 10; i++) {
      expect(budget.nextDelayMs()).toBe(0);
      budget.record();
    }
    expect(budget.nextDelayMs()).toBe(60_000);

    now = 30_000;
    expect(budget.nextDelayMs()).toBe(30_000);

    now = 60_001;
    expect(budget.nextDelayMs()).toBe(0);
  });
});

describe('buildSearchQuery', () => {
  test('keeps salient keywords and drops stopwords and punctuation', () => {
    const query = buildSearchQuery('Do you encrypt customer data at rest?');
    expect(query).toContain('encrypt');
    expect(query).toContain('customer');
    expect(query).toContain('data');
    expect(query).not.toMatch(/\bdo\b/i);
    expect(query).not.toMatch(/\byou\b/i);
    expect(query).not.toContain('?');
  });

  test('caps very long questions to a bounded number of keywords', () => {
    const long = Array.from({ length: 60 }, (_, i) => `keyword${i}`).join(' ') + '?';
    const query = buildSearchQuery(long);
    expect(query.split(' ').length).toBeLessThanOrEqual(8);
  });

  test('expand mode groups known compliance terms with OR synonyms', () => {
    const query = buildSearchQuery('Do you encrypt customer data at rest?', { expand: true });
    expect(query).toMatch(/\bencrypt\b/);
    expect(query).toMatch(/\bencryption\b/);
    expect(query).toContain('OR');
  });
});

describe('QueryPlanner — synonym expansion fallback', () => {
  test('retries with expanded query when literal query returns zero hits', async () => {
    let call = 0;
    const { client, calls } = fakeRts((params) => {
      call++;
      if (params.query.includes('encryption') || params.query.includes('encrypted')) {
        return [{ permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0', snippet: 'encryption at rest' }];
      }
      return []; // literal "encrypt" returns nothing
    });
    const planner = new QueryPlanner(client, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    });

    const result = await planner.retrieve([q('q1', 'Do you encrypt data at rest?')], { strategy: 'per-question' });

    expect(calls).toHaveLength(2);
    expect(result.get('q1')?.hits).toHaveLength(1);
    expect(result.get('q1')?.hits[0]?.permalink).toBe('https://s.example/enc');
  });

  test('does not retry expansion when literal query already returns hits', async () => {
    const { client, calls } = fakeRts(() => [
      { permalink: 'https://s.example/ok', channelId: 'C1', ts: '1.0', snippet: 'ok' },
    ]);
    const planner = new QueryPlanner(client, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    });

    await planner.retrieve([q('q1', 'Do you encrypt data at rest?')], { strategy: 'per-question' });
    expect(calls).toHaveLength(1);
  });
});

describe('QueryPlanner — per-question strategy (primary)', () => {
  test('issues exactly one RTS call per question and attributes hits directly', async () => {
    const { client, calls } = fakeRts((params) => [
      {
        permalink: `https://s.example/${params.query.split(' ')[0]}`,
        channelId: 'C1',
        ts: '1.0',
        snippet: `evidence for: ${params.query}`,
      },
    ]);
    const planner = new QueryPlanner(client, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    });

    const questions = [q('q1', 'Do you encrypt data at rest?'), q('q2', 'Is MFA enforced for employees?')];
    const result = await planner.retrieve(questions, { strategy: 'per-question' });

    expect(calls).toHaveLength(2);
    expect(result.get('q1')?.hits).toHaveLength(1);
    expect(result.get('q2')?.hits).toHaveLength(1);
    expect(result.get('q1')?.hits[0]?.snippet).toContain('encrypt');
  });

  test('a failing search marks that question search_failed without killing the run', async () => {
    const { client } = fakeRts((params) =>
      params.query.includes('encrypt') ? new Error('rts_unavailable') : [
        { permalink: 'https://s.example/ok', channelId: 'C1', ts: '1.0', snippet: 'ok' },
      ],
    );
    const planner = new QueryPlanner(client, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    });

    const result = await planner.retrieve(
      [q('q1', 'Do you encrypt data at rest?'), q('q2', 'Is MFA enforced?')],
      { strategy: 'per-question' },
    );

    expect(result.get('q1')?.searchFailed).toBe(true);
    expect(result.get('q1')?.hits).toHaveLength(0);
    expect(result.get('q2')?.searchFailed).toBe(false);
    expect(result.get('q2')?.hits).toHaveLength(1);
  });

  test('respects the rate budget by sleeping for the budget delay', async () => {
    let now = 0;
    const sleeps: number[] = [];
    const { client } = fakeRts(() => []);
    const planner = new QueryPlanner(client, {
      budget: new RateBudget({ maxPerWindow: 2, windowMs: 60_000, now: () => now }),
      sleep: async (ms) => {
        sleeps.push(ms);
        now += ms; // simulate time passing
      },
    });

    const questions = [q('q1', 'encrypt data rest?'), q('q2', 'mfa enforced?'), q('q3', 'backups tested?')];
    await planner.retrieve(questions, { strategy: 'per-question' });

    // Third call must have waited for the 60s window.
    expect(sleeps.some((ms) => ms >= 60_000)).toBe(true);
  });
});

describe('QueryPlanner — OR-batch strategy (degraded mode)', () => {
  test('groups questions into batches of at most 5 per call', async () => {
    const { client, calls } = fakeRts(() => []);
    const planner = new QueryPlanner(client, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    });

    const questions = Array.from({ length: 12 }, (_, i) => q(`q${i + 1}`, `unique topic${i} question?`));
    await planner.retrieve(questions, { strategy: 'or-batch' });

    expect(calls).toHaveLength(3); // 5 + 5 + 2
    expect(calls[0]?.query).toContain(' OR ');
  });

  test('attributes batched hits to the question with highest token overlap', async () => {
    const { client } = fakeRts(() => [
      { permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0', snippet: 'we encrypt data at rest with KMS' },
      { permalink: 'https://s.example/mfa', channelId: 'C1', ts: '2.0', snippet: 'MFA is enforced for employees via Okta' },
    ]);
    const planner = new QueryPlanner(client, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    });

    const result = await planner.retrieve(
      [q('q1', 'Do you encrypt data at rest?'), q('q2', 'Is MFA enforced for employees?')],
      { strategy: 'or-batch' },
    );

    expect(result.get('q1')?.hits.map((h) => h.permalink)).toEqual(['https://s.example/enc']);
    expect(result.get('q2')?.hits.map((h) => h.permalink)).toEqual(['https://s.example/mfa']);
  });
});
