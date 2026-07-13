import { describe, test, expect } from 'vitest';
import {
  QueryPlanner,
  RateBudget,
  type RtsClient,
  type RtsHit,
  type RtsSearchParams,
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

function plannerOpts(signature: () => string, requesterId?: string, now?: () => number) {
  return {
    budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
    sleep: async () => {},
    cache: {
      ttlMs: 300_000,
      signature,
      ...(requesterId ? { requesterId } : {}),
      ...(now ? { now } : {}),
    },
  };
}

describe('QueryPlanner delta-scoped cache', () => {
  test('caches hits and returns them when the evidence signature is unchanged', async () => {
    const { client, calls } = fakeRts((params) => [
      {
        permalink: `https://s.example/${params.query.split(' ')[0]}`,
        channelId: 'C1',
        ts: '1.0',
        snippet: `evidence for: ${params.query}`,
      },
    ]);
    const planner = new QueryPlanner(client, plannerOpts(() => 'sig1'));

    const questions = [q('q1', 'Do you encrypt data at rest?')];
    const r1 = await planner.retrieve(questions, { strategy: 'per-question' });
    const r2 = await planner.retrieve(questions, { strategy: 'per-question' });

    expect(calls).toHaveLength(1);
    expect(r1.get('q1')?.hits).toHaveLength(1);
    expect(r2.get('q1')?.hits[0]?.permalink).toBe(r1.get('q1')?.hits[0]?.permalink);
  });

  test('similar questions share a cached query key', async () => {
    const { client, calls } = fakeRts(() => [
      { permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0', snippet: 'we encrypt data at rest' },
    ]);
    const planner = new QueryPlanner(client, plannerOpts(() => 'sig1'));

    await planner.retrieve([q('q1', 'Do you encrypt data at rest?')], { strategy: 'per-question' });
    await planner.retrieve([q('q2', 'How do you encrypt data at rest?')], { strategy: 'per-question' });

    // Both questions normalize to the same keyword query.
    expect(calls).toHaveLength(1);
  });

  test('invalidates the cache when the evidence signature changes', async () => {
    let signature = 'sig1';
    const { client, calls } = fakeRts(() => [
      { permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0', snippet: 'we encrypt data at rest' },
    ]);
    const planner = new QueryPlanner(client, plannerOpts(() => signature));

    const questions = [q('q1', 'Do you encrypt data at rest?')];
    await planner.retrieve(questions, { strategy: 'per-question' });
    signature = 'sig2';
    await planner.retrieve(questions, { strategy: 'per-question' });

    expect(calls).toHaveLength(2);
  });

  test('requester ids scope the cache', async () => {
    const { client, calls } = fakeRts(() => [
      { permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0', snippet: 'we encrypt data at rest' },
    ]);
    const plannerA = new QueryPlanner(client, plannerOpts(() => 'sig1', 'U_A'));
    const plannerB = new QueryPlanner(client, plannerOpts(() => 'sig1', 'U_B'));

    const questions = [q('q1', 'Do you encrypt data at rest?')];
    await plannerA.retrieve(questions, { strategy: 'per-question' });
    await plannerB.retrieve(questions, { strategy: 'per-question' });

    expect(calls).toHaveLength(2);
  });

  test('respects TTL and expires stale entries', async () => {
    let now = 0;
    const { client, calls } = fakeRts(() => [
      { permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0', snippet: 'we encrypt data at rest' },
    ]);
    const planner = new QueryPlanner(
      client,
      plannerOpts(() => 'sig1', undefined, () => now),
    );

    const questions = [q('q1', 'Do you encrypt data at rest?')];
    await planner.retrieve(questions, { strategy: 'per-question' });

    now = 299_999;
    await planner.retrieve(questions, { strategy: 'per-question' });
    expect(calls).toHaveLength(1);

    now = 300_001;
    await planner.retrieve(questions, { strategy: 'per-question' });
    expect(calls).toHaveLength(2);
  });

  test('warm pre-loads the cache without a second RTS call', async () => {
    const { client, calls } = fakeRts(() => [
      { permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0', snippet: 'we encrypt data at rest' },
    ]);
    const planner = new QueryPlanner(client, plannerOpts(() => 'sig1'));

    const questions = [q('q1', 'Do you encrypt data at rest?')];
    await planner.warm(questions);
    await planner.retrieve(questions, { strategy: 'per-question' });

    expect(calls).toHaveLength(1);
  });
});
