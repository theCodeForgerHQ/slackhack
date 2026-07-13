import { describe, test, expect } from 'vitest';
import { checkPermissionInvariant, checkPermissionInvariantBatch } from '../src/core/invariantMonitor.js';
import type { DraftResult } from '../src/core/pipeline.js';
import type { VisibilityChecker } from '../src/core/library.js';

function result(overrides: Partial<DraftResult> & Pick<DraftResult, 'questionId' | 'state'>): DraftResult {
  return {
    questionText: 'q',
    ...overrides,
  } as DraftResult;
}

const visibility: VisibilityChecker = {
  async canSee(_userId, citation) {
    return citation.permalink.startsWith('p/public');
  },
};

describe('Permission invariant monitor', () => {
  test('passes for grounded answer with visible citations', async () => {
    const r = result({
      questionId: 'q1',
      state: 'grounded',
      answerText: 'Yes.',
      citations: [{ permalink: 'p/public-1', channelId: 'C1', ts: '1.0' }],
    });
    const check = await checkPermissionInvariant(r, 'U1', visibility);
    expect(check.ok).toBe(true);
    expect(check.violations).toHaveLength(0);
  });

  test('fails for grounded answer with an invisible citation', async () => {
    const r = result({
      questionId: 'q1',
      state: 'grounded',
      answerText: 'Yes.',
      citations: [{ permalink: 'p/private-1', channelId: 'C1', ts: '1.0' }],
    });
    const check = await checkPermissionInvariant(r, 'U1', visibility);
    expect(check.ok).toBe(false);
    expect(check.violations[0]).toContain('p/private-1');
  });

  test('passes vacuously for needs_sme with no answer text', async () => {
    const r = result({ questionId: 'q1', state: 'needs_sme', reason: 'no_evidence' });
    const check = await checkPermissionInvariant(r, 'U1', visibility);
    expect(check.ok).toBe(true);
  });

  test('fails when answer text has no citations', async () => {
    const r = result({ questionId: 'q1', state: 'grounded', answerText: 'Yes.' });
    const check = await checkPermissionInvariant(r, 'U1', visibility);
    expect(check.ok).toBe(false);
    expect(check.violations[0]).toContain('zero citations');
  });

  test('batch check reports all violations', async () => {
    const rs = [
      result({ questionId: 'q1', state: 'grounded', answerText: 'Yes.', citations: [{ permalink: 'p/public-1', channelId: 'C1', ts: '1.0' }] }),
      result({ questionId: 'q2', state: 'grounded', answerText: 'Yes.', citations: [{ permalink: 'p/private-1', channelId: 'C1', ts: '1.0' }] }),
    ];
    const batch = await checkPermissionInvariantBatch(rs, 'U1', visibility);
    expect(batch.ok).toBe(false);
    expect(batch.violations).toHaveLength(1);
    expect(batch.violations[0]?.questionId).toBe('q2');
  });
});
