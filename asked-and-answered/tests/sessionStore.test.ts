import { describe, it, expect } from 'vitest';
import { InMemorySessionStore, SqliteSessionStore } from '../src/slack/sessionStore.js';
import type { DraftResult } from '../src/core/pipeline.js';
import type { PlanCounts } from '../src/slack/blocks.js';

const sampleResults: DraftResult[] = [
  {
    questionId: 'q1',
    questionText: 'What?',
    state: 'grounded',
    answerText: 'Yes.',
    citations: [{ permalink: 'p/1', channelId: 'C1', ts: '1' }],
  },
];

const sampleCounts: PlanCounts = {
  total: 1,
  deduped: 1,
  verified: 0,
  grounded: 1,
  needsSme: 0,
};

function testStore(name: string, create: () => InMemorySessionStore | SqliteSessionStore) {
  describe(name, () => {
    it('saves and loads a session', () => {
      const store = create();
      const record = {
        runId: 'run-1',
        requesterId: 'U1',
        results: sampleResults,
        counts: sampleCounts,
        confirmedQuestionIds: ['q1'],
        confirmedBy: { q1: 'U_SME' },
        updatedAt: new Date().toISOString(),
      };
      store.save(record);
      const loaded = store.load('run-1');
      expect(loaded).toEqual(record);
    });

    it('returns undefined for missing sessions', () => {
      const store = create();
      expect(store.load('missing')).toBeUndefined();
    });

    it('updates an existing session', () => {
      const store = create();
      store.save({ runId: 'run-1', requesterId: 'U1', results: sampleResults, counts: sampleCounts, confirmedQuestionIds: [], confirmedBy: {}, updatedAt: new Date().toISOString() });
      const updated = {
        runId: 'run-1',
        requesterId: 'U1',
        results: [],
        counts: { total: 0, deduped: 0, verified: 0, grounded: 0, needsSme: 0 },
        confirmedQuestionIds: [],
        confirmedBy: {},
        updatedAt: new Date().toISOString(),
      };
      store.save(updated);
      expect(store.load('run-1')).toEqual(updated);
    });

    it('deletes a session', () => {
      const store = create();
      const record = { runId: 'run-1', requesterId: 'U1', results: sampleResults, counts: sampleCounts, confirmedQuestionIds: [], confirmedBy: {}, updatedAt: new Date().toISOString() };
      store.save(record);
      store.delete('run-1');
      expect(store.load('run-1')).toBeUndefined();
    });

    it('prunes stale sessions', () => {
      const store = create();
      const old = new Date(Date.now() - 7 * 60 * 60 * 1000).toISOString();
      const recent = new Date().toISOString();
      store.save({ runId: 'old', requesterId: 'U1', results: sampleResults, counts: sampleCounts, confirmedQuestionIds: [], confirmedBy: {}, updatedAt: old });
      store.save({ runId: 'recent', requesterId: 'U1', results: sampleResults, counts: sampleCounts, confirmedQuestionIds: [], confirmedBy: {}, updatedAt: recent });
      store.prune(6 * 60 * 60 * 1000);
      expect(store.load('old')).toBeUndefined();
      expect(store.load('recent')).toBeDefined();
    });

    it('counts open reviews across sessions', () => {
      const store = create();
      store.save({
        runId: 'run-1',
        requesterId: 'U1',
        results: [
          { questionId: 'q1', questionText: 'A', state: 'grounded', answerText: 'a', citations: [] },
          { questionId: 'q2', questionText: 'B', state: 'verified', answerText: 'b', citations: [] },
          { questionId: 'q3', questionText: 'C', state: 'needs_sme' },
        ] as DraftResult[],
        counts: { total: 3, deduped: 3, verified: 1, grounded: 1, needsSme: 1 },
        confirmedQuestionIds: [],
        confirmedBy: {},
        updatedAt: new Date().toISOString(),
      });
      store.save({
        runId: 'run-2',
        requesterId: 'U2',
        results: [{ questionId: 'q4', questionText: 'D', state: 'grounded', answerText: 'd', citations: [] }] as DraftResult[],
        counts: { total: 1, deduped: 1, verified: 0, grounded: 1, needsSme: 0 },
        confirmedQuestionIds: [],
        confirmedBy: {},
        updatedAt: new Date().toISOString(),
      });
      expect(store.countOpenReviews()).toBe(3);
    });
  });
}

testStore('InMemorySessionStore', () => new InMemorySessionStore());
testStore('SqliteSessionStore', () => SqliteSessionStore.inMemory());
