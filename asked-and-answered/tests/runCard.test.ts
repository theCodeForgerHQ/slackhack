import { describe, test, expect } from 'vitest';
import { createHash } from 'node:crypto';
import { agentRunCardBlocks, signedAuditText } from '../src/slack/blocks.js';
import type { DraftResult } from '../src/core/pipeline.js';

function result(overrides: Partial<DraftResult> & Pick<DraftResult, 'questionId' | 'state'>): DraftResult {
  return {
    questionText: `Question for ${overrides.questionId}`,
    ...overrides,
  } as DraftResult;
}

function expectedSignature(
  runId: string,
  r: DraftResult,
  confirmActor?: string,
  approveActor?: string,
): string {
  const citations = (r.citations ?? []).map((c) => c.permalink).join(',');
  const actors = [confirmActor, approveActor].filter(Boolean).join('|');
  const payload = `${runId}:${r.questionId}:${r.answerText ?? r.reason ?? ''}:${citations}:${actors}`;
  return createHash('sha256').update(payload).digest('hex');
}

describe('agentRunCardBlocks', () => {
  test('renders a signed card for a grounded answer', () => {
    const r = result({
      questionId: 'q1',
      state: 'grounded',
      answerText: 'Quarterly restore drills.',
      citations: [{ permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' }],
    });
    const runId = 'run-abc';
    const sigs = { timestamp: '2026-07-14T00:00:00.000Z', confirmActor: 'U_CONF', approveActor: 'U_APP' };
    const blocks = agentRunCardBlocks(r, runId, sigs);
    const json = JSON.stringify(blocks);

    expect(json).toContain('Quarterly restore drills.');
    expect(json).toContain('run-abc');
    expect(json).toContain('U_CONF');
    expect(json).toContain('U_APP');
    expect(json).toContain(expectedSignature(runId, r, 'U_CONF', 'U_APP'));
  });

  test('renders a signed card for a needs_sme result', () => {
    const r = result({ questionId: 'q2', state: 'needs_sme', reason: 'no_evidence' });
    const runId = 'run-xyz';
    const blocks = agentRunCardBlocks(r, runId, { timestamp: '2026-07-14T00:00:00.000Z' });
    const json = JSON.stringify(blocks);

    expect(json).toContain('Needs SME');
    expect(json).toContain('no evidence');
    expect(json).toContain(expectedSignature(runId, r));
  });
});

describe('signedAuditText', () => {
  test('produces a stable plain-text audit line', () => {
    const r = result({
      questionId: 'q1',
      state: 'verified',
      answerText: 'Yes.',
      citations: [{ permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' }],
      approvedBy: 'U_APP',
      approvedAt: '2026-07-14T00:00:00.000Z',
    });
    const runId = 'run-abc';
    const sigs = { timestamp: '2026-07-14T00:00:00.000Z', approveActor: 'U_APP' };
    const line = signedAuditText(r, runId, sigs);

    expect(line).toContain('run=run-abc');
    expect(line).toContain('q=q1');
    expect(line).toContain('state=verified');
    expect(line).toContain(expectedSignature(runId, r, undefined, 'U_APP'));
  });

  test('signature changes when the answer changes', () => {
    const runId = 'run-abc';
    const sigs = { timestamp: '2026-07-14T00:00:00.000Z' };
    const a = result({ questionId: 'q1', state: 'grounded', answerText: 'Answer A.' });
    const b = result({ questionId: 'q1', state: 'grounded', answerText: 'Answer B.' });

    expect(signedAuditText(a, runId, sigs)).not.toBe(signedAuditText(b, runId, sigs));
  });
});
