import { describe, test, expect } from 'vitest';
import { decide } from '../src/core/decide.js';
import type { DraftResultLike } from '../src/core/decide.js';
import { HIGH_SENSITIVITY_POLICY } from '../src/core/policy.js';

function groundedResult(questionId: string, questionText: string, answerText: string): DraftResultLike {
  return {
    questionId,
    questionText,
    state: 'grounded',
    answerText,
    citations: [{ permalink: 'p/enc', channelId: 'C1', ts: '1' }],
  };
}

describe('decide', () => {
  test('Confirm emits AnswerConfirmed', () => {
    const result = decide([], {
      type: 'Confirm',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Do you encrypt?', 'Yes.'),
    });
    expect(result.ok).toBe(true);
    expect(result.events).toHaveLength(1);
    expect(result.events?.[0]?.type).toBe('AnswerConfirmed');
  });

  test('Approve emits AnswerApproved after Confirm', () => {
    const confirmed = decide([], {
      type: 'Confirm',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Do you encrypt?', 'Yes.'),
    });
    const result = decide(confirmed.events ?? [], {
      type: 'Approve',
      questionId: 'q1',
      actor: 'U_REVIEWER',
      actorType: 'human',
      result: groundedResult('q1', 'Do you encrypt?', 'Yes.'),
    });
    expect(result.ok).toBe(true);
    expect(result.events).toHaveLength(1);
    expect(result.events?.[0]?.type).toBe('AnswerApproved');
    expect(result.finalApproval).toBe(true);
  });

  test('Approve without Confirm fails', () => {
    const result = decide([], {
      type: 'Approve',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Do you encrypt?', 'Yes.'),
    });
    expect(result.ok).toBe(false);
  });

  test('Approve by the same human who confirmed fails', () => {
    const confirmed = decide([], {
      type: 'Confirm',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Do you encrypt?', 'Yes.'),
    });
    const result = decide(confirmed.events ?? [], {
      type: 'Approve',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Do you encrypt?', 'Yes.'),
    });
    expect(result.ok).toBe(false);
  });

  test('Approve without answer text fails', () => {
    const result = decide([], {
      type: 'Approve',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: { questionId: 'q1', questionText: 'Q', state: 'needs_sme', reason: 'no_evidence' },
    });
    expect(result.ok).toBe(false);
  });

  test('Reject emits AnswerRejected', () => {
    const result = decide([], {
      type: 'Reject',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Q', 'Yes.'),
    });
    expect(result.ok).toBe(true);
    expect(result.events?.[0]?.type).toBe('AnswerRejected');
  });

  test('Reject is idempotent', () => {
    const first = decide([], {
      type: 'Reject',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Q', 'Yes.'),
    });
    const second = decide(first.events ?? [], {
      type: 'Reject',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Q', 'Yes.'),
    });
    expect(second.ok).toBe(true);
    expect(second.events).toHaveLength(0);
  });

  test('Edit emits AnswerEdited', () => {
    const result = decide([], {
      type: 'Edit',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      newText: 'Updated answer.',
      result: groundedResult('q1', 'Q', 'Yes.'),
    });
    expect(result.ok).toBe(true);
    expect(result.events?.[0]?.type).toBe('AnswerEdited');
  });

  test('SmeProvide emits DraftProduced and AnswerConfirmed', () => {
    const result = decide([], {
      type: 'SmeProvide',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      answerText: 'SME answer.',
      result: { questionId: 'q1', questionText: 'Q', state: 'needs_sme', reason: 'no_evidence' },
    });
    expect(result.ok).toBe(true);
    expect(result.events?.map((e) => e.type)).toEqual(['DraftProduced', 'AnswerConfirmed']);
  });

  test('Propose emits AnswerProposed', () => {
    const result = decide([], {
      type: 'Propose',
      answerId: 42,
      questionText: 'Q',
      answerText: 'A',
      citations: [],
    });
    expect(result.ok).toBe(true);
    expect(result.events?.[0]?.type).toBe('AnswerProposed');
  });

  test('Propose is blocked for already-proposed answer', () => {
    const first = decide([], {
      type: 'Propose',
      answerId: 42,
      questionText: 'Q',
      answerText: 'A',
      citations: [],
    });
    const second = decide(first.events ?? [], {
      type: 'Propose',
      answerId: 42,
      questionText: 'Q',
      answerText: 'A',
      citations: [],
    });
    expect(second.ok).toBe(false);
  });

  test('Export emits Exported', () => {
    const result = decide([], { type: 'Export', runId: 'r1', actor: 'U_SME', actorType: 'human' });
    expect(result.ok).toBe(true);
    expect(result.events?.[0]?.type).toBe('Exported');
  });

  test('Approve by agent is rejected — human gate', () => {
    const result = decide([], {
      type: 'Approve',
      questionId: 'q1',
      actor: 'AGENT',
      actorType: 'agent',
      result: groundedResult('q1', 'Do you encrypt?', 'Yes.'),
    });
    expect(result.ok).toBe(false);
  });

  test('Reject by agent is rejected — human gate', () => {
    const result = decide([], {
      type: 'Reject',
      questionId: 'q1',
      actor: 'AGENT',
      actorType: 'agent',
      result: groundedResult('q1', 'Q', 'Yes.'),
    });
    expect(result.ok).toBe(false);
  });

  test('N-of-M: first approval is not final when policy requires two approvers', () => {
    const confirmed = decide([], {
      type: 'Confirm',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Is the breach response classified?', 'Yes.'),
    });
    const first = decide(confirmed.events ?? [], {
      type: 'Approve',
      questionId: 'q1',
      actor: 'U_REVIEWER1',
      actorType: 'human',
      result: groundedResult('q1', 'Is the breach response classified?', 'Yes.'),
      policy: HIGH_SENSITIVITY_POLICY,
    });
    expect(first.ok).toBe(true);
    expect(first.finalApproval).toBe(false);

    const second = decide([...(confirmed.events ?? []), ...(first.events ?? [])], {
      type: 'Approve',
      questionId: 'q1',
      actor: 'U_REVIEWER2',
      actorType: 'human',
      result: groundedResult('q1', 'Is the breach response classified?', 'Yes.'),
      policy: HIGH_SENSITIVITY_POLICY,
    });
    expect(second.ok).toBe(true);
    expect(second.finalApproval).toBe(true);
  });

  test('N-of-M: duplicate approver is idempotent and does not advance final count', () => {
    const confirmed = decide([], {
      type: 'Confirm',
      questionId: 'q1',
      actor: 'U_SME',
      actorType: 'human',
      result: groundedResult('q1', 'Is the breach response classified?', 'Yes.'),
    });
    const first = decide(confirmed.events ?? [], {
      type: 'Approve',
      questionId: 'q1',
      actor: 'U_REVIEWER1',
      actorType: 'human',
      result: groundedResult('q1', 'Is the breach response classified?', 'Yes.'),
      policy: HIGH_SENSITIVITY_POLICY,
    });
    const dup = decide([...(confirmed.events ?? []), ...(first.events ?? [])], {
      type: 'Approve',
      questionId: 'q1',
      actor: 'U_REVIEWER1',
      actorType: 'human',
      result: groundedResult('q1', 'Is the breach response classified?', 'Yes.'),
      policy: HIGH_SENSITIVITY_POLICY,
    });
    expect(dup.ok).toBe(true);
    expect(dup.events).toHaveLength(0);
    expect(dup.finalApproval).toBe(false);
  });
});
