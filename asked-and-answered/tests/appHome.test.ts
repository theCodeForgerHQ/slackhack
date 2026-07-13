import { describe, test, expect } from 'vitest';
import { AnswerLibrary } from '../src/core/library.js';
import { LedgerV2 } from '../src/core/ledgerV2.js';
import { appHomeBlocks, gatherHomeStats } from '../src/slack/appHome.js';

describe('gatherHomeStats', () => {
  test('reports zero state on empty library and ledger', async () => {
    const library = AnswerLibrary.inMemory();
    const ledger = LedgerV2.inMemory();
    const stats = await gatherHomeStats(library, ledger);

    expect(stats.questionnairesRun).toBe(0);
    expect(stats.verifiedAnswers).toBe(0);
    expect(stats.smeTestimonyAnswers).toBe(0);
    expect(stats.ledgerEntries).toBe(0);
    expect(stats.ledgerOk).toBe(true);
    expect(stats.recentAnswers).toHaveLength(0);
    expect(stats.recentRuns).toHaveLength(0);
  });

  test('counts verified vs expert-typed answers and ledger questionnaires', async () => {
    const library = AnswerLibrary.inMemory();
    const ledger = LedgerV2.inMemory();

    library.saveApproved({
      questionText: 'Q1',
      answerText: 'A1',
      citations: [{ permalink: 'https://s.example/p1', channelId: 'C1', ts: '1.0' }],
      approvedBy: 'U1',
    });
    library.saveApproved({
      questionText: 'Q2',
      answerText: 'A2',
      citations: [],
      approvedBy: 'U2',
      kind: 'sme_testimony',
    });

    ledger.append({ type: 'QuestionnaireIntaken', runId: 'r1', questions: [], requesterId: 'U1', ts: new Date().toISOString() });
    ledger.append({ type: 'QuestionnaireIntaken', runId: 'r2', questions: [], requesterId: 'U2', ts: new Date().toISOString() });

    const visibility = { canSee: async () => true };
    const stats = await gatherHomeStats(library, ledger, 'U1', visibility);
    expect(stats.verifiedAnswers).toBe(1);
    expect(stats.smeTestimonyAnswers).toBe(1);
    expect(stats.questionnairesRun).toBe(2);
    expect(stats.ledgerEntries).toBe(2);
    expect(stats.recentAnswers).toHaveLength(2);
    expect(stats.recentRuns).toHaveLength(2);
    expect(stats.recentRuns[0]?.questions).toBe(0);
  });

  test('ledgerOk becomes false when the chain is tampered', async () => {
    const library = AnswerLibrary.inMemory();
    const ledger = LedgerV2.inMemory();
    ledger.append({ type: 'QuestionnaireIntaken', runId: 'r1', questions: [], requesterId: 'U1', ts: new Date().toISOString() });

    // Tamper with the stored payload directly via the DB.
    // @ts-expect-error private access for test
    ledger.db.prepare("UPDATE ledger_v2 SET payload = '{}' WHERE seq = 0").run();

    const stats = await gatherHomeStats(library, ledger);
    expect(stats.ledgerOk).toBe(false);
  });

  test('filters recent answers by viewer ACL (fail-closed)', async () => {
    const library = AnswerLibrary.inMemory();
    const ledger = LedgerV2.inMemory();

    library.saveApproved({
      questionText: 'Visible Q',
      answerText: 'Visible A',
      citations: [{ permalink: 'https://s.example/p1', channelId: 'C_PUBLIC', ts: '1.0' }],
      approvedBy: 'U1',
    });
    library.saveApproved({
      questionText: 'Private Q',
      answerText: 'Private A',
      citations: [{ permalink: 'https://s.example/p2', channelId: 'C_PRIVATE', ts: '2.0' }],
      approvedBy: 'U1',
    });

    const visibility = {
      canSee: async (userId: string, citation: { channelId: string }) =>
        citation.channelId === 'C_PUBLIC' && userId === 'U_VIEWER',
    };

    const stats = await gatherHomeStats(library, ledger, 'U_VIEWER', visibility);
    expect(stats.recentAnswers).toHaveLength(1);
    expect(stats.recentAnswers[0]?.questionText).toBe('Visible Q');
  });
});

describe('appHomeBlocks', () => {
  test('renders header, stats, health, actions, and recent answers', () => {
    const blocks = appHomeBlocks({
      questionnairesRun: 5,
      verifiedAnswers: 3,
      smeTestimonyAnswers: 1,
      ledgerEntries: 12,
      ledgerOk: true,
      invariantOk: true,
      recentRuns: [
        { runId: 'run-abc-123', when: '2026-07-11T10:00:00.000Z', questions: 12 },
      ],
      recentAnswers: [
        {
          questionText: 'Do you encrypt data at rest?',
          answerText: 'Yes — AES-256.',
          approvedBy: 'U_SME',
          approvedAt: '2026-07-11T10:00:00.000Z',
          kind: 'evidence',
        },
      ],
    });
    const json = JSON.stringify(blocks);

    expect(json).toContain('Compliance memory');
    expect(json).toContain('Questionnaires run');
    expect(json).toContain('Verified answers');
    expect(json).toContain('Ledger integrity');
    expect(json).toContain('Permission invariant');
    expect(json).toContain('apphome_run_questionnaire');
    expect(json).toContain('apphome_verify_ledger');
    expect(json).toContain('apphome_check_invariant');
    expect(json).toContain('Do you encrypt data at rest?');
  });

  test('adds invariant URL button when public URL is provided', () => {
    const blocks = appHomeBlocks(
      {
        questionnairesRun: 0,
        verifiedAnswers: 0,
        smeTestimonyAnswers: 0,
        ledgerEntries: 0,
        ledgerOk: true,
        invariantOk: true,
        recentRuns: [],
        recentAnswers: [],
      },
      { invariantCheckUrl: 'https://example.com/invariant' },
    );
    const json = JSON.stringify(blocks);
    expect(json).toContain('https://example.com/invariant');
    expect(json).toContain('apphome_open_invariant');
  });
});
