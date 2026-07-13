import { describe, test, expect } from 'vitest';
import { createCanvasOrFallback } from '../src/slack/canvasCreate.js';
import { buildCanvasDocument } from '../src/slack/canvasExport.js';
import type { DraftResult } from '../src/core/pipeline.js';

function fakeClient(overrides: {
  createResult?: { ok: false; error: string } | { canvas_id: string };
  uploadOk?: boolean;
} = {}) {
  const uploads: unknown[] = [];
  const client = {
    canvases: {
      create: async () => {
        if (!('canvas_id' in overrides.createResult!)) {
          const err = new Error(`OpenAI request failed: 400 ${overrides.createResult?.error ?? ''}`);
          (err as any).data = overrides.createResult;
          throw err;
        }
        return overrides.createResult;
      },
    },
    files: {
      uploadV2: async (args: unknown) => {
        uploads.push(args);
        return { ok: overrides.uploadOk ?? true };
      },
    },
  };
  return { client: client as any, uploads };
}

const result: DraftResult = {
  questionId: 'q1',
  questionText: 'Do you encrypt data at rest?',
  state: 'grounded',
  answerText: 'Yes — AES-256.',
  citations: [{ permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0' }],
};

describe('createCanvasOrFallback', () => {
  test('returns native canvas when API succeeds', async () => {
    const { client } = fakeClient({ createResult: { canvas_id: 'C123' }, uploadOk: true });
    const doc = buildCanvasDocument([result], { runId: 'r1', requesterId: 'U1', title: 'T' });
    const res = await createCanvasOrFallback(client, 'C', '1.0', doc);
    expect(res.kind).toBe('native');
    expect(res.canvasId).toBe('C123');
  });

  test('returns scope_missing and does not fall back on missing_scope', async () => {
    const { client, uploads } = fakeClient({ createResult: { ok: false, error: 'missing_scope' } });
    const doc = buildCanvasDocument([result], { runId: 'r1', requesterId: 'U1', title: 'T' });
    const res = await createCanvasOrFallback(client, 'C', '1.0', doc);
    expect(res.kind).toBe('scope_missing');
    expect(uploads).toHaveLength(0);
  });

  test('falls back to Markdown on transient API errors', async () => {
    const { client, uploads } = fakeClient({ createResult: { ok: false, error: 'internal_error' } });
    const doc = buildCanvasDocument([result], { runId: 'r1', requesterId: 'U1', title: 'T' });
    const res = await createCanvasOrFallback(client, 'C', '1.0', doc);
    expect(res.kind).toBe('markdown_fallback');
    expect(uploads.length).toBeGreaterThan(0);
  });
});
