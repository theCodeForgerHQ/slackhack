import { describe, test, expect, beforeEach, afterEach } from 'vitest';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import Database from 'better-sqlite3';
import { LedgerV2 } from '../../src/core/ledgerV2.js';
import type { DomainEvent } from '../../src/core/events.js';

describe('Ledger SQLite on-disk integration', () => {
  let dir: string;
  let path: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), 'aa-ledger-test-'));
    path = join(dir, 'ledger.db');
  });

  afterEach(() => {
    rmSync(dir, { recursive: true, force: true });
  });

  test('writes and reads events from a real SQLite file', () => {
    const ledger = LedgerV2.atPath(path);
    const event: DomainEvent = {
      type: 'AnswerApproved',
      ts: new Date().toISOString(),
      actor: 'U_TEST',
      actorType: 'human',
      answerId: 1,
      answerText: 'We encrypt data at rest.',
      citations: [{ permalink: 'https://s.example/p', channelId: 'C1', ts: '1.0' }],
      questionText: 'Do you encrypt data at rest?',
    };
    ledger.append(event);
    expect(ledger.entries()).toHaveLength(1);
    expect(ledger.entries()[0]).toEqual(event);
  });

  test('hash chain verifies across multiple on-disk entries', () => {
    const ledger = LedgerV2.atPath(path);
    for (let i = 0; i < 5; i++) {
      ledger.append({
        type: 'AnswerApproved',
        ts: new Date().toISOString(),
        actor: 'U_TEST',
        actorType: 'human',
        answerId: i,
        answerText: `answer ${i}`,
        citations: [],
        questionText: `q${i}`,
      });
    }
    const v = ledger.verify();
    expect(v.ok).toBe(true);
    expect(v.entriesChecked).toBe(5);
  });

  test('detects tampering in the SQLite file', () => {
    const ledger = LedgerV2.atPath(path);
    ledger.append({
      type: 'AnswerApproved',
      ts: new Date().toISOString(),
      actor: 'U_TEST',
      actorType: 'human',
      answerId: 1,
      answerText: 'We encrypt data at rest.',
      citations: [],
      questionText: 'Do you encrypt data at rest?',
    });
    const raw = new Database(path);
    raw.prepare("UPDATE ledger_v2 SET actor = 'U_EVIL' WHERE seq = 0").run();
    raw.close();

    const reloaded = LedgerV2.atPath(path);
    const v = reloaded.verify();
    expect(v.ok).toBe(false);
    expect(v.firstBadSeq).toBe(0);
  });
});
