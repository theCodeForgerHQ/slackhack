import { describe, test, expect, beforeEach } from 'vitest';
import { runQuestionnaire, ReviewSession, type RunDeps } from '../src/slack/flows.js';
import { AnswerLibrary, type VisibilityChecker } from '../src/core/library.js';
import { Ledger } from '../src/core/ledger.js';
import { QueryPlanner, RateBudget, type RtsClient } from '../src/core/planner.js';
import type { DraftingLlm } from '../src/core/pipeline.js';
import { parseText } from '../src/core/parse.js';

const allVisible: VisibilityChecker = { canSee: async () => true };

function deps(overrides: Partial<RunDeps> = {}): RunDeps {
  const rts: RtsClient = {
    async searchContext(params) {
      if (params.query.includes('encrypt')) {
        return {
          hits: [
            { permalink: 'https://s.example/enc', channelId: 'C1', ts: '1.0', snippet: 'we use AES-256 KMS encryption at rest' },
          ],
        };
      }
      return { hits: [] };
    },
  };
  const llm: DraftingLlm = {
    async draft(_q, hits) {
      const snippet = hits[0]?.snippet ?? '';
      return {
        kind: 'answer',
        answerText: `Yes — ${snippet}.`,
        citedPermalinks: [hits[0]?.permalink ?? ''],
      };
    },
  };
  return {
    library: AnswerLibrary.inMemory(),
    ledger: Ledger.inMemory(),
    llm,
    visibility: allVisible,
    planner: new QueryPlanner(rts, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    }),
    ...overrides,
  };
}

describe('runQuestionnaire', () => {
  test('produces mixed states and accurate counts, reporting progress', async () => {
    const d = deps();
    const parsed = parseText(['Do you encrypt data at rest?', 'Do you carry cyber liability insurance?'].join('\n'));
    const progress: string[] = [];

    const session = await runQuestionnaire(parsed, 'U_REQ', d, (msg) => progress.push(msg));

    expect(session.results).toHaveLength(2);
    expect(session.counts).toEqual({ total: 2, deduped: 2, verified: 0, grounded: 1, needsSme: 1 });
    expect(progress.length).toBeGreaterThanOrEqual(2);
  });

  test('previously approved answers come back verified on the next run (compounding)', async () => {
    const d = deps();
    const parsed = parseText('Do you encrypt data at rest?');

    const run1 = await runQuestionnaire(parsed, 'U_REQ', d, () => {});
    expect(run1.results[0]?.state).toBe('grounded');

    run1.confirm('q1', 'U_SME');
    run1.approve('q1', 'U_REVIEWER');

    const run2 = await runQuestionnaire(parsed, 'U_REQ2', d, () => {});
    expect(run2.results[0]?.state).toBe('verified');
    expect(run2.results[0]?.approvedBy).toBe('U_REVIEWER');
  });
});

describe('ReviewSession actions', () => {
  let d: RunDeps;
  let session: ReviewSession;

  beforeEach(async () => {
    d = deps();
    const parsed = parseText('Do you encrypt data at rest?');
    session = await runQuestionnaire(parsed, 'U_REQ', d, () => {});
  });

  test('approve appends to the ledger and saves to the library after confirm', () => {
    session.confirm('q1', 'U_SME');
    session.approve('q1', 'U_REVIEWER');

    const entries = d.ledger.entries();
    expect(entries).toHaveLength(2);
    expect(entries[0]?.action).toBe('confirm');
    expect(entries[1]?.action).toBe('approve');
    expect(entries[1]?.actor).toBe('U_REVIEWER');
    expect(d.library.searchAnswers('encrypt data at rest')).toHaveLength(1);
    expect(session.results[0]?.state).toBe('verified');
  });

  test('reject appends to the ledger and downgrades the row to needs_sme', () => {
    session.reject('q1', 'U_SME');

    expect(d.ledger.entries()[0]?.action).toBe('reject');
    expect(session.results[0]?.state).toBe('needs_sme');
    expect(session.results[0]?.answerText).toBeUndefined();
    expect(d.library.searchAnswers('encrypt data at rest')).toHaveLength(0);
  });

  test('edit replaces the answer text, logs an edit, and saves the edited version on confirm+approve', () => {
    session.edit('q1', 'U_SME', 'Yes — AES-256; keys rotate every 90 days.');
    session.confirm('q1', 'U_SME');
    session.approve('q1', 'U_REVIEWER');

    const actions = d.ledger.entries().map((e) => e.action);
    expect(actions).toEqual(['edit', 'confirm', 'approve']);
    expect(d.library.searchAnswers('encrypt')[0]?.answerText).toContain('90 days');
  });

  test('smeProvide answers a needs_sme question with SME text and confirms it for final approval', async () => {
    const parsed = parseText('Do you carry cyber liability insurance?');
    const s2 = await runQuestionnaire(parsed, 'U_REQ', d, () => {});
    expect(s2.results[0]?.state).toBe('needs_sme');

    s2.smeProvide('q1', 'U_SME', 'Yes, $5M coverage via Acme Insurance, renewed annually.');

    expect(s2.results[0]?.state).toBe('grounded');
    expect(s2.confirmedQuestionIds.has('q1')).toBe(true);
    expect(d.ledger.entries().at(-1)?.action).toBe('confirm');
    expect(d.library.searchAnswers('cyber liability insurance')).toHaveLength(0);

    s2.approve('q1', 'U_REVIEWER');
    expect(s2.results[0]?.state).toBe('verified');
    expect(d.library.searchAnswers('cyber liability insurance')).toHaveLength(1);
  });

  test('approving a needs_sme row without SME text is impossible', () => {
    expect(() => session.approve('missing', 'U_SME')).toThrow();
  });

  test('each run has a unique runId so stale buttons cannot cross sessions', async () => {
    const parsed = parseText('Do you encrypt data at rest?');
    const s1 = await runQuestionnaire(parsed, 'U_REQ', deps(), () => {});
    const s2 = await runQuestionnaire(parsed, 'U_REQ', deps(), () => {});
    expect(s1.runId).toBeTruthy();
    expect(s1.runId).not.toBe(s2.runId);
  });

  test('acting with a mismatched runId is rejected', () => {
    expect(() => session.approve('q1', 'U_SME', 'not-this-run')).toThrow(/stale|run/i);
  });

  test('acting with the correct runId succeeds', () => {
    session.confirm('q1', 'U_SME', session.runId);
    expect(() => session.approve('q1', 'U_REVIEWER', session.runId)).not.toThrow();
  });

  test('re-approving an already-verified answer is a no-op (no duplicate ledger/library rows)', () => {
    session.confirm('q1', 'U_SME');
    session.approve('q1', 'U_REVIEWER');
    session.approve('q1', 'U_REVIEWER');
    session.approve('q1', 'U_REVIEWER');
    expect(d.ledger.entries()).toHaveLength(2);
    expect(d.library.searchAnswers('encrypt data at rest')).toHaveLength(1);
  });
});
