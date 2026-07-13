import { describe, test, expect, beforeEach, afterEach } from 'vitest';
import { rmSync, existsSync } from 'node:fs';
import { AnswerLibrary } from '../src/core/library.js';
import { Ledger } from '../src/core/ledger.js';
import { LedgerV2 } from '../src/core/ledgerV2.js';
import { EvidenceGraph } from '../src/core/evidenceGraph.js';
import { ConformalMatcher } from '../src/core/conformal.js';
import { DEFAULT_CALIBRATION_PAIRS } from '../src/core/calibrationData.js';
import { QueryPlanner, RateBudget, type RtsClient } from '../src/core/planner.js';
import { parseText } from '../src/core/parse.js';
import { runQuestionnaire, ReviewSession, type RunDeps } from '../src/slack/flows.js';
import type { DraftingLlm, DraftResult } from '../src/core/pipeline.js';

const dbPath = '/tmp/aa-integration-test.db';

function cleanup(): void {
  for (const p of [dbPath, dbPath.replace(/\.db$/, '-ledger.db'), dbPath.replace(/\.db$/, '-ledger-v2.db')]) {
    if (existsSync(p)) rmSync(p);
  }
}

function deps(): RunDeps {
  cleanup();
  const graph = new EvidenceGraph();
  const matcher = new ConformalMatcher();
  matcher.calibrate(DEFAULT_CALIBRATION_PAIRS);
  const library = AnswerLibrary.atPath(dbPath, graph, matcher);
  library.rebuildGraph();
  const ledger = Ledger.atPath(dbPath.replace(/\.db$/, '-ledger.db'));
  const ledgerV2 = LedgerV2.atPath(dbPath.replace(/\.db$/, '-ledger-v2.db'));

  const rts: RtsClient = {
    async searchContext(params) {
      if (params.query.includes('encrypt')) {
        return {
          hits: [
            { permalink: 'https://s.example/enc', channelId: 'C_PUBLIC', ts: '1.0', snippet: 'we use AES-256 KMS encryption at rest' },
          ],
        };
      }
      if (params.query.includes('insurance')) {
        return {
          hits: [
            { permalink: 'https://s.example/ins', channelId: 'C_PRIVATE', ts: '2.0', snippet: 'cyber liability policy is $5M via Acme' },
          ],
        };
      }
      return { hits: [] };
    },
  };

  const llm: DraftingLlm = {
    async draft(_q, hits) {
      const h = hits[0];
      if (!h) return { kind: 'refuse', reason: 'no evidence' };
      return { kind: 'answer', answerText: `Yes — ${h.snippet}.`, citedPermalinks: [h.permalink] };
    },
  };

  return {
    library,
    ledger,
    ledgerV2,
    llm,
    visibility: {
      async canSee(userId, citation) {
        // Simulate a private channel only visible to U_PRIVATE.
        if (citation.channelId === 'C_PRIVATE' && userId !== 'U_PRIVATE') return false;
        return true;
      },
    },
    planner: new QueryPlanner(rts, {
      budget: new RateBudget({ maxPerWindow: 100, windowMs: 60_000, now: () => 0 }),
      sleep: async () => {},
    }),
  };
}

describe('integration: full questionnaire lifecycle with real SQLite', () => {
  let d: RunDeps;

  beforeEach(() => {
    d = deps();
  });

  afterEach(() => {
    cleanup();
  });

  test('run → approve → second run auto-verifies, ledgers chain correctly', async () => {
    const parsed = parseText('Do you encrypt data at rest?');

    const run1 = await runQuestionnaire(parsed, 'U_PUBLIC', d, () => {});
    expect(run1.results[0]?.state).toBe('grounded');

    run1.confirm('q1', 'U_SME');
    run1.approve('q1', 'U_REVIEWER');

    const run2 = await runQuestionnaire(parsed, 'U_PUBLIC', d, () => {});
    expect(run2.results[0]?.state).toBe('verified');
    expect(run2.results[0]?.approvedBy).toBe('U_REVIEWER');

    expect(d.ledger.verify().ok).toBe(true);
    expect(d.ledgerV2!.verify().ok).toBe(true);
  });

  test('private-channel evidence is invisible to unauthorized requester', async () => {
    const parsed = parseText('Do you carry cyber liability insurance?');
    const run = await runQuestionnaire(parsed, 'U_PUBLIC', d, () => {});

    // The LLM drafted from private evidence, but the ACL check should degrade.
    expect(run.results[0]?.state).toBe('needs_sme');
    expect(run.results[0]?.reason).toBe('acl_degraded');
  });

  test('tampering with ledgerV2 breaks verification', async () => {
    const parsed = parseText('Do you encrypt data at rest?');
    const run = await runQuestionnaire(parsed, 'U_PUBLIC', d, () => {});
    run.confirm('q1', 'U_SME');
    run.approve('q1', 'U_REVIEWER');

    expect(d.ledgerV2!.verify().ok).toBe(true);

    // Tamper with the stored payload directly.
    // @ts-expect-error private access for test
    d.ledgerV2!.db.prepare("UPDATE ledger_v2 SET payload = '{}' WHERE seq = 0").run();

    expect(d.ledgerV2!.verify().ok).toBe(false);
  });

  test('rejected answer does not enter the library and remains needs_sme on next run', async () => {
    const parsed = parseText('Do you encrypt data at rest?');
    const run1 = await runQuestionnaire(parsed, 'U_PUBLIC', d, () => {});
    run1.reject('q1', 'U_REVIEWER');

    const run2 = await runQuestionnaire(parsed, 'U_PUBLIC', d, () => {});
    expect(run2.results[0]?.state).toBe('grounded');
    expect(d.library.searchAnswers('encrypt data at rest')).toHaveLength(0);
  });

  test('sessions survive process restart via durable SQLite session store', async () => {
    const { SqliteSessionStore } = await import('../src/slack/sessionStore.js');
    const sessionDb = dbPath.replace(/\.db$/, '-sessions.db');
    if (existsSync(sessionDb)) rmSync(sessionDb);
    const store = SqliteSessionStore.atPath(sessionDb);

    const parsed = parseText('Do you encrypt data at rest?');
    const run = await runQuestionnaire(parsed, 'U_PUBLIC', d, () => {});
    run.confirm('q1', 'U_SME');
    store.save({
      runId: run.runId,
      requesterId: run.requesterId,
      results: run.results,
      counts: run.recount(),
      confirmedQuestionIds: Array.from(run.confirmedQuestionIds),
      updatedAt: new Date().toISOString(),
    });

    const loaded = store.load(run.runId);
    expect(loaded).toBeDefined();
    expect(loaded?.results).toHaveLength(1);

    const reconstructed = ReviewSession.fromState(
      { runId: loaded!.runId, results: loaded!.results, counts: loaded!.counts, requesterId: loaded!.requesterId, confirmedQuestionIds: loaded!.confirmedQuestionIds ?? [] },
      d,
    );
    reconstructed.approve('q1', 'U_REVIEWER');
    expect(d.library.searchAnswers('encrypt data at rest')).toHaveLength(1);

    rmSync(sessionDb);
  });
});
