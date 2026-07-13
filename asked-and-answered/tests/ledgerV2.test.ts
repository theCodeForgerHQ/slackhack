import { describe, test, expect } from 'vitest';
import type Database from 'better-sqlite3';
import { LedgerV2, computeHash } from '../src/core/ledgerV2.js';
import type { AnswerApproved } from '../src/core/events.js';

function dbOf(ledger: LedgerV2): Database.Database {
  return (ledger as unknown as { db: Database.Database }).db;
}

describe('LedgerV2', () => {
  test('append and retrieve DomainEvents', () => {
    const ledger = LedgerV2.inMemory();
    ledger.append({
      type: 'AnswerApproved',
      answerId: 1,
      questionText: 'Q',
      answerText: 'A',
      citations: [],
      actor: 'U_SME',
      actorType: 'human',
      ts: '2026-01-01',
    });

    const entries = ledger.entries();
    expect(entries).toHaveLength(1);
    expect(entries[0]?.type).toBe('AnswerApproved');
  });

  test('verify passes for intact chain', () => {
    const ledger = LedgerV2.inMemory();
    ledger.append({
      type: 'AnswerApproved',
      answerId: 1,
      questionText: 'Q',
      answerText: 'A',
      citations: [],
      actor: 'U_SME',
      actorType: 'human',
      ts: '2026-01-01',
    });

    const verdict = ledger.verify();
    expect(verdict.ok).toBe(true);
  });

  test('verify fails when chain hash is broken', () => {
    const ledger = LedgerV2.inMemory();
    ledger.append({
      type: 'AnswerApproved',
      answerId: 1,
      questionText: 'Q',
      answerText: 'A',
      citations: [],
      actor: 'U_SME',
      actorType: 'human',
      ts: '2026-01-01',
    });

    dbOf(ledger).prepare('UPDATE ledger_v2 SET actor = ? WHERE seq = ?').run('U_ATTACKER', 0);

    const verdict = ledger.verify();
    expect(verdict.ok).toBe(false);
  });

  test('verify detects metadata inconsistency', () => {
    const ledger = LedgerV2.inMemory();
    ledger.append({
      type: 'AnswerApproved',
      answerId: 1,
      questionText: 'Q',
      answerText: 'A',
      citations: [],
      actor: 'U_SME',
      actorType: 'human',
      ts: '2026-01-01',
    } as AnswerApproved);

    // Mutate the stored actor column (not the payload) and recompute the hash
    // so the chain still links. Verification must catch the column/payload mismatch.
    const raw = ledger.rows()[0]!;
    const tampered: Omit<typeof raw, 'hash'> = { ...raw, actor: 'U_ATTACKER' };
    const newHash = computeHash(tampered);
    dbOf(ledger)
      .prepare('UPDATE ledger_v2 SET actor = ?, hash = ? WHERE seq = ?')
      .run('U_ATTACKER', newHash, raw.seq);

    const verdict = ledger.verify();
    expect(verdict.ok).toBe(false);
    expect(verdict.metadataMismatch).toContain('metadata does not match payload');
  });
});
