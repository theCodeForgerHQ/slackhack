import { describe, test, expect } from 'vitest';
import { exportToSlackList } from '../src/slack/listsExport.js';
import type { DraftResult } from '../src/core/pipeline.js';

function fakeClient(error?: string) {
  const calls: { method: string; args: unknown }[] = [];
  return {
    calls,
    client: {
      apiCall: async (method: string, args?: Record<string, unknown>) => {
        calls.push({ method, args });
        if (error) {
          const err = new Error(`Slack API error: ${error}`);
          (err as any).data = { error };
          throw err;
        }
        if (method === 'lists.create') return { ok: true, list_id: 'L123' };
        return { ok: true };
      },
    } as any,
  };
}

const grounded: DraftResult = {
  questionId: 'q1',
  questionText: 'Do you encrypt data at rest?',
  state: 'grounded',
  answerText: 'Yes — AES-256.',
  citations: [{ permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0' }],
};

describe('exportToSlackList', () => {
  test('creates a list and adds items for grounded/verified answers', async () => {
    const { client, calls } = fakeClient();
    const res = await exportToSlackList(client, [grounded], { runId: 'r1', requesterId: 'U1' });
    expect(res.ok).toBe(true);
    expect(res.listId).toBe('L123');
    expect(calls.some((c) => c.method === 'lists.create')).toBe(true);
    expect(calls.some((c) => c.method === 'lists.edit')).toBe(true);
  });

  test('returns fallback reason on missing_scope', async () => {
    const { client } = fakeClient('missing_scope');
    const res = await exportToSlackList(client, [grounded], { runId: 'r1', requesterId: 'U1' });
    expect(res.ok).toBe(false);
    expect(res.fallbackReason).toContain('missing_scope');
  });
});
