import { describe, test, expect } from 'vitest';
import { DecisionGraph } from '../src/core/decisionGraph.js';
import { detectDrift } from '../src/core/driftResolver.js';

describe('DecisionGraph', () => {
  test('builds a supersedes chain when boolean values reverse', () => {
    const g = new DecisionGraph();
    g.addEvidence('p/old', 'C1', '1.0', 'MFA is not enforced for employees.');
    g.addEvidence('p/new', 'C1', '2.0', 'MFA is enforced for every employee via Okta since 2024.');

    const rows = g.resolve('Is MFA enforced for all employees?');
    expect(rows.length).toBeGreaterThan(0);
    expect(rows[0]?.reversed).toBe(true);
    expect(rows[0]?.currentValue.toLowerCase()).toContain('enforced');
  });

  test('ignores evidence unrelated to the question topic', () => {
    const g = new DecisionGraph();
    g.addEvidence('p/enc1', 'C1', '1.0', 'Yes, customer data is encrypted at rest with AES-256.');
    g.addEvidence('p/enc2', 'C1', '2.0', 'Data is encrypted at rest with AWS KMS.');
    g.addEvidence('p/ins', 'C2', '2.0', 'Cyber liability policy is $5M.');

    const rows = g.resolve('Do you encrypt data at rest?');
    expect(rows.some((r) => r.topic === 'boolean')).toBe(true);
    expect(rows.some((r) => r.topic === 'money')).toBe(false);
  });

  test('does not flag drift when values agree', () => {
    const g = new DecisionGraph();
    g.addEvidence('p/old', 'C1', '1.0', 'MFA is enforced for all employees.');
    g.addEvidence('p/new', 'C1', '2.0', 'MFA is enforced for every employee via Okta.');

    const rows = g.resolve('Is MFA enforced for all employees?');
    expect(rows.length).toBeGreaterThan(0);
    expect(rows[0]?.reversed).toBe(false);
  });
});

describe('detectDrift', () => {
  test('flags an approved answer contradicted by newer evidence', () => {
    const drift = detectDrift(
      {
        id: 1,
        questionText: 'Is MFA enforced?',
        answerText: 'No, MFA is not enforced.',
        citations: [{ permalink: 'p/old', channelId: 'C1', ts: '1.0' }],
        approvedBy: 'U_SME',
        approvedAt: '2026-01-01',
        kind: 'evidence',
      },
      [
        { permalink: 'p/old', channelId: 'C1', ts: '1.0', snippet: 'MFA is not enforced.' },
        { permalink: 'p/new', channelId: 'C1', ts: '2.0', snippet: 'MFA is enforced for every employee.' },
      ],
    );
    expect(drift.drift).toBe(true);
  });
});
