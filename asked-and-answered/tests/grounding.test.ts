import { describe, test, expect } from 'vitest';
import { GroundingGate } from '../src/core/grounding.js';
import type { RtsHit } from '../src/core/planner.js';

function hit(permalink: string, snippet: string): RtsHit {
  return { permalink, channelId: 'C1', ts: '1.0', snippet };
}

describe('GroundingGate', () => {
  const gate = new GroundingGate();

  test('passes when answer contains the cited snippet verbatim', () => {
    const result = gate.verify(
      'Yes, all customer data is encrypted at rest with AES-256 managed by AWS KMS.',
      [hit('p/enc', 'All customer data is encrypted at rest with AES-256 managed by AWS KMS.')],
      ['p/enc'],
    );
    expect(result.ok).toBe(true);
    expect(result.failures).toHaveLength(0);
  });

  test('passes when cited snippet contains the answer claim', () => {
    const result = gate.verify(
      'Customer data is encrypted at rest with AES-256.',
      [hit('p/enc', 'All customer data is encrypted at rest with AES-256 managed by AWS KMS.')],
      ['p/enc'],
    );
    expect(result.ok).toBe(true);
  });

  test('passes for a close paraphrase after normalization', () => {
    const result = gate.verify(
      'MFA is enforced for every employee via Okta, with no exceptions since 2024.',
      [hit('p/mfa', 'MFA is enforced for every employee via Okta; no exceptions since 2024.')],
      ['p/mfa'],
    );
    expect(result.ok).toBe(true);
  });

  test('fails when citation is not in evidence set', () => {
    const result = gate.verify('Yes.', [hit('p/enc', 'encrypted at rest')], ['p/missing']);
    expect(result.ok).toBe(false);
    expect(result.failures[0]?.reason).toBe('missing_source');
  });

  test('fails when answer fabricates a claim not in evidence', () => {
    const result = gate.verify(
      'We carry a $5 million cyber liability insurance policy.',
      [hit('p/enc', 'All customer data is encrypted at rest with AES-256.')],
      ['p/enc'],
    );
    expect(result.ok).toBe(false);
  });

  test('fails when paraphrase is too loose', () => {
    const result = gate.verify(
      'We use quantum cryptography everywhere.',
      [hit('p/enc', 'All customer data is encrypted at rest with AES-256.')],
      ['p/enc'],
    );
    expect(result.ok).toBe(false);
  });

  test('normalizes unicode and punctuation before comparing', () => {
    const result = gate.verify(
      'Customer data is encrypted at rest with AES 256',
      [hit('p/enc', 'All customer data is encrypted at rest with AES-256 managed by AWS KMS.')],
      ['p/enc'],
    );
    expect(result.ok).toBe(true);
  });

  test('handles NFKC normalization of fancy quotes and em-dashes', () => {
    const result = gate.verify(
      'MFA is enforced for every employee via Okta—no exceptions since 2024.',
      [hit('p/mfa', 'MFA is enforced for every employee via Okta; no exceptions since 2024.')],
      ['p/mfa'],
    );
    expect(result.ok).toBe(true);
  });

  test('multiple citations: passes only if all are grounded', () => {
    const result = gate.verify(
      'All customer data is encrypted at rest with AES-256. MFA is enforced for every employee via Okta; no exceptions since 2024.',
      [
        hit('p/enc', 'All customer data is encrypted at rest with AES-256.'),
        hit('p/mfa', 'MFA is enforced for every employee via Okta; no exceptions since 2024.'),
      ],
      ['p/enc', 'p/mfa'],
    );
    expect(result.ok).toBe(true);
  });

  test('multiple citations: fails if any is ungrounded', () => {
    const result = gate.verify(
      'All customer data is encrypted at rest with AES-256, and we carry cyber insurance.',
      [
        hit('p/enc', 'All customer data is encrypted at rest with AES-256.'),
        hit('p/mfa', 'MFA is enforced for every employee via Okta; no exceptions since 2024.'),
      ],
      ['p/enc', 'p/mfa'],
    );
    expect(result.ok).toBe(false);
    expect(result.failures).toHaveLength(1);
    expect(result.failures[0]?.permalink).toBe('p/mfa');
  });

  test('ignores duplicate citations', () => {
    const result = gate.verify(
      'Customer data is encrypted at rest with AES-256.',
      [hit('p/enc', 'All customer data is encrypted at rest with AES-256.')],
      ['p/enc', 'p/enc'],
    );
    expect(result.ok).toBe(true);
  });

  test('empty answer is ungrounded', () => {
    const result = gate.verify('   ', [hit('p/enc', 'encrypted at rest')], ['p/enc']);
    expect(result.ok).toBe(false);
  });
});
