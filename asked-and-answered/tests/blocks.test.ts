import { describe, test, expect } from 'vitest';
import {
  reviewTableBlocks,
  answerCardBlocks,
  smeRequestBlocks,
  verifyResultBlocks,
  planSummaryText,
} from '../src/slack/blocks.js';
import type { DraftResult } from '../src/core/pipeline.js';

function result(overrides: Partial<DraftResult> & Pick<DraftResult, 'questionId' | 'state'>): DraftResult {
  return {
    questionText: `Question for ${overrides.questionId}`,
    ...overrides,
  } as DraftResult;
}

const MIXED: DraftResult[] = [
  result({
    questionId: 'q1',
    state: 'verified',
    answerText: 'Yes.',
    citations: [{ permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' }],
    approvedBy: 'U_SME',
    approvedAt: '2026-07-11T10:00:00.000Z',
  }),
  result({
    questionId: 'q2',
    state: 'grounded',
    answerText: 'Quarterly restore drills.',
    citations: [{ permalink: 'https://s.example/p2', channelId: 'C2', ts: '2.0' }],
  }),
  result({ questionId: 'q3', state: 'needs_sme', reason: 'no_evidence' }),
];

describe('planSummaryText', () => {
  test('reports parsed/deduped/state counts', () => {
    const text = planSummaryText({ total: 47, deduped: 41, verified: 12, grounded: 20, needsSme: 9 });
    expect(text).toContain('47');
    expect(text).toContain('41');
    expect(text).toContain('12');
    expect(text).toContain('20');
    expect(text).toContain('9');
  });
});

describe('reviewTableBlocks (fallback surface)', () => {
  test('renders one section per question with status emoji and a review button', () => {
    const blocks = reviewTableBlocks(MIXED, { page: 0 });
    const json = JSON.stringify(blocks);

    expect(json).toContain('Question for q1');
    expect(json).toContain('Question for q3');
    // Every row carries an action to open its card.
    const buttons = blocks.filter(
      (b) => (b as { accessory?: { action_id?: string } }).accessory?.action_id === 'open_answer_card',
    );
    expect(buttons.length).toBe(3);
  });

  test('paginates at 20 rows and includes next-page navigation', () => {
    const many = Array.from({ length: 25 }, (_, i) =>
      result({ questionId: `q${i + 1}`, state: 'needs_sme', reason: 'no_evidence' }),
    );
    const page0 = reviewTableBlocks(many, { page: 0 });
    const page1 = reviewTableBlocks(many, { page: 1 });

    const rows = (blocks: unknown[]) =>
      blocks.filter(
        (b) => (b as { accessory?: { action_id?: string } }).accessory?.action_id === 'open_answer_card',
      ).length;

    expect(rows(page0)).toBe(20);
    expect(rows(page1)).toBe(5);
    expect(JSON.stringify(page0)).toContain('table_next_page');
    expect(JSON.stringify(page1)).not.toContain('table_next_page');
  });

  test('needs_sme rows show the refusal reason, not an empty answer', () => {
    const blocks = reviewTableBlocks([MIXED[2] as DraftResult], { page: 0 });
    const json = JSON.stringify(blocks);
    expect(json).toMatch(/no evidence/i);
  });
});

describe('answerCardBlocks', () => {
  test('grounded card shows draft, citations, and confirm/edit/reject buttons', () => {
    const blocks = answerCardBlocks(MIXED[1] as DraftResult);
    const json = JSON.stringify(blocks);

    expect(json).toContain('Quarterly restore drills.');
    expect(json).toContain('https://s.example/p2');
    expect(json).toContain('"action_id":"confirm_answer"');
    expect(json).toContain('"action_id":"reject_answer"');
    expect(json).toContain('"action_id":"edit_answer"');
  });

  test('confirmed grounded card shows approve instead of confirm', () => {
    const blocks = answerCardBlocks(MIXED[1] as DraftResult, '', true);
    const json = JSON.stringify(blocks);

    expect(json).toContain('"action_id":"approve_answer"');
    expect(json).not.toContain('"action_id":"confirm_answer"');
  });

  test('verified card shows the approval provenance', () => {
    const blocks = answerCardBlocks(MIXED[0] as DraftResult);
    const json = JSON.stringify(blocks);
    expect(json).toContain('U_SME');
    expect(json).toMatch(/verified/i);
  });

  test('needs_sme card has a route-to-SME button and NO approve button', () => {
    const blocks = answerCardBlocks(MIXED[2] as DraftResult);
    const json = JSON.stringify(blocks);
    expect(json).toContain('"action_id":"route_to_sme"');
    expect(json).not.toContain('"action_id":"approve_answer"');
  });
});

describe('smeRequestBlocks', () => {
  test('DM to the SME carries the question, requester, and answer box', () => {
    const blocks = smeRequestBlocks({
      questionText: 'Do you carry cyber liability insurance?',
      requesterId: 'U_REQ',
      ref: 'run-abc:q3',
    });
    const json = JSON.stringify(blocks);
    expect(json).toContain('cyber liability insurance');
    expect(json).toContain('U_REQ');
    expect(json).toContain('"action_id":"sme_provide_answer"');
  });
});

describe('verifyResultBlocks', () => {
  test('clean chain renders a passing message with entry count', () => {
    const blocks = verifyResultBlocks({ ok: true, entriesChecked: 12 });
    expect(JSON.stringify(blocks)).toContain('12');
    expect(JSON.stringify(blocks)).toMatch(/intact|verified|passed/i);
  });

  test('tampered chain names the first bad entry', () => {
    const blocks = verifyResultBlocks({ ok: false, entriesChecked: 12, firstBadSeq: 4 });
    const json = JSON.stringify(blocks);
    expect(json).toMatch(/tamper|failed|broken/i);
    expect(json).toContain('4');
  });
});
