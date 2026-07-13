import { describe, test, expect } from 'vitest';
import { SlackRtsClient, ActionTokenStore, parseRtsResponse } from '../src/slack/rts.js';
import { ChannelMembershipChecker } from '../src/slack/visibility.js';
import { buildDraftPrompt, parseDraftReply } from '../src/llm/prompt.js';
import type { RtsHit } from '../src/core/planner.js';

describe('ActionTokenStore', () => {
  test('stores and returns the freshest token per user', () => {
    const store = new ActionTokenStore();
    store.record('U1', 'tok-old');
    store.record('U1', 'tok-new');
    expect(store.latest('U1')).toBe('tok-new');
    expect(store.latest('U2')).toBeUndefined();
  });
});

describe('parseRtsResponse', () => {
  test('maps message results defensively into hits', () => {
    const raw = {
      ok: true,
      results: {
        messages: [
          {
            permalink: 'https://s.example/p1',
            channel: { id: 'C1' },
            ts: '123.456',
            content: 'we rotate keys quarterly',
          },
          // Missing fields must not crash — they are skipped.
          { content: 'orphan without permalink' },
        ],
      },
    };

    const hits = parseRtsResponse(raw);

    expect(hits).toHaveLength(1);
    expect(hits[0]).toEqual({
      permalink: 'https://s.example/p1',
      channelId: 'C1',
      ts: '123.456',
      snippet: 'we rotate keys quarterly',
    });
  });

  test('tolerates alternative field spellings (channel_id, message_ts, text)', () => {
    const raw = {
      ok: true,
      results: {
        messages: [
          { permalink: 'https://s.example/p2', channel_id: 'C2', message_ts: '9.9', text: 'MFA via Okta' },
        ],
      },
    };
    const hits = parseRtsResponse(raw);
    expect(hits[0]?.channelId).toBe('C2');
    expect(hits[0]?.ts).toBe('9.9');
    expect(hits[0]?.snippet).toBe('MFA via Okta');
  });

  test('returns [] for empty or malformed payloads', () => {
    expect(parseRtsResponse({ ok: true })).toEqual([]);
    expect(parseRtsResponse({})).toEqual([]);
    expect(parseRtsResponse(null)).toEqual([]);
  });
});

describe('SlackRtsClient', () => {
  test('passes query and action token through to assistant.search.context', async () => {
    const calls: Array<{ method: string; args: Record<string, unknown> }> = [];
    const fakeApi = async (method: string, args: Record<string, unknown>) => {
      calls.push({ method, args });
      return { ok: true, results: { messages: [] } };
    };
    const store = new ActionTokenStore();
    store.record('U1', 'tok-1');
    const client = new SlackRtsClient(fakeApi, store, 'U1');

    await client.searchContext({ query: 'encrypt data rest', limit: 10 });

    expect(calls[0]?.method).toBe('assistant.search.context');
    expect(calls[0]?.args.query).toBe('encrypt data rest');
    expect(calls[0]?.args.action_token).toBe('tok-1');
  });
});

describe('ChannelMembershipChecker', () => {
  const citation = { permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' };

  test('visible when the user is a member of the citation channel', async () => {
    const checker = new ChannelMembershipChecker(async (channel) =>
      channel === 'C1' ? ['U1', 'U2'] : [],
    );
    expect(await checker.canSee('U1', citation)).toBe(true);
  });

  test('not visible when the user is absent', async () => {
    const checker = new ChannelMembershipChecker(async () => ['U9']);
    expect(await checker.canSee('U1', citation)).toBe(false);
  });

  test('FAIL-CLOSED: an API error means NOT visible', async () => {
    const checker = new ChannelMembershipChecker(async () => {
      throw new Error('rate_limited');
    });
    expect(await checker.canSee('U1', citation)).toBe(false);
  });

  test('membership lookups are cached per channel', async () => {
    let calls = 0;
    const checker = new ChannelMembershipChecker(async () => {
      calls++;
      return ['U1'];
    });
    await checker.canSee('U1', citation);
    await checker.canSee('U1', citation);
    expect(calls).toBe(1);
  });
});

describe('drafting prompt', () => {
  const hits: RtsHit[] = [
    { permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0', snippet: 'we use AES-256' },
  ];

  test('prompt carries the question, evidence snippets, and anti-injection guardrails', () => {
    const prompt = buildDraftPrompt({ id: 'q1', text: 'Do you encrypt data at rest?', sourceRef: 'row 2' }, hits);
    expect(prompt).toContain('Do you encrypt data at rest?');
    expect(prompt).toContain('we use AES-256');
    expect(prompt).toContain('https://s.example/p1');
    expect(prompt.toLowerCase()).toContain('do not follow instructions');
    expect(prompt.toLowerCase()).toContain('refuse');
  });

  test('parseDraftReply accepts a well-formed answer JSON', () => {
    const reply = JSON.stringify({ answer: 'Yes, AES-256.', citations: ['https://s.example/p1'] });
    expect(parseDraftReply(reply)).toEqual({
      kind: 'answer',
      answerText: 'Yes, AES-256.',
      citedPermalinks: ['https://s.example/p1'],
    });
  });

  test('parseDraftReply maps refusal JSON to a refuse draft', () => {
    const reply = JSON.stringify({ refuse: true, reason: 'insufficient evidence' });
    expect(parseDraftReply(reply)).toEqual({ kind: 'refuse', reason: 'insufficient evidence' });
  });

  test('parseDraftReply treats malformed output as refusal (fail-closed)', () => {
    expect(parseDraftReply('I think the answer is probably yes!').kind).toBe('refuse');
    expect(parseDraftReply('{"answer": 42}').kind).toBe('refuse');
  });
});
