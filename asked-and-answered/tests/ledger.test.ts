import { describe, test, expect, beforeEach } from 'vitest';
import { Ledger } from '../src/core/ledger.js';
import { tamperLedger } from './helpers/tamper.js';

describe('Ledger', () => {
  let ledger: Ledger;

  beforeEach(() => {
    ledger = Ledger.inMemory();
  });

  test('appends entries and verify() passes on an untampered chain', () => {
    ledger.append({
      action: 'approve',
      actor: 'U123',
      questionId: 'q1',
      answerHashInput: 'We encrypt data at rest with AES-256.',
      evidenceRefs: ['https://slack.example/archives/C1/p1', 'https://slack.example/archives/C1/p2'],
    });
    ledger.append({
      action: 'reject',
      actor: 'U456',
      questionId: 'q2',
      answerHashInput: 'Draft that was wrong.',
      evidenceRefs: [],
    });

    const result = ledger.verify();

    expect(result.ok).toBe(true);
    expect(result.entriesChecked).toBe(2);
    expect(ledger.entries()).toHaveLength(2);
  });

  test('each entry chains to the previous entry hash', () => {
    const e1 = ledger.append({
      action: 'approve',
      actor: 'U1',
      questionId: 'q1',
      answerHashInput: 'a',
      evidenceRefs: [],
    });
    const e2 = ledger.append({
      action: 'approve',
      actor: 'U1',
      questionId: 'q2',
      answerHashInput: 'b',
      evidenceRefs: [],
    });

    expect(e2.prevHash).toBe(e1.hash);
    expect(e1.prevHash).toBe('GENESIS');
    expect(e1.hash).toMatch(/^[0-9a-f]{64}$/);
  });

  test('verify() detects tampering with an entry field and names the row', () => {
    ledger.append({ action: 'approve', actor: 'U1', questionId: 'q1', answerHashInput: 'a', evidenceRefs: [] });
    ledger.append({ action: 'approve', actor: 'U1', questionId: 'q2', answerHashInput: 'b', evidenceRefs: [] });
    ledger.append({ action: 'edit', actor: 'U2', questionId: 'q3', answerHashInput: 'c', evidenceRefs: [] });

    tamperLedger(ledger, 1, { actor: 'U999' });

    const result = ledger.verify();

    expect(result.ok).toBe(false);
    expect(result.firstBadSeq).toBe(1);
  });

  test('verify() detects a broken chain link (entry re-written with valid self-hash)', () => {
    ledger.append({ action: 'approve', actor: 'U1', questionId: 'q1', answerHashInput: 'a', evidenceRefs: [] });
    ledger.append({ action: 'approve', actor: 'U1', questionId: 'q2', answerHashInput: 'b', evidenceRefs: [] });

    tamperLedger(ledger, 0, { answerHash: 'deadbeef'.repeat(8) }, { rehashSelf: true });

    const result = ledger.verify();

    expect(result.ok).toBe(false);
    expect(result.firstBadSeq).toBeLessThanOrEqual(1);
  });

  test('answer text is stored only as a hash, never verbatim', () => {
    const secret = 'Our root AWS account password is hunter2';
    ledger.append({
      action: 'approve',
      actor: 'U1',
      questionId: 'q1',
      answerHashInput: secret,
      evidenceRefs: [],
    });

    const serialized = JSON.stringify(ledger.entries());

    expect(serialized).not.toContain('hunter2');
  });
});
