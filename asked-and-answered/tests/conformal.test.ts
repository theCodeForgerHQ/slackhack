import { describe, test, expect } from 'vitest';
import { ConformalMatcher } from '../src/core/conformal.js';
import type { ApprovedAnswer } from '../src/core/library.js';

function answer(id: number, questionText: string): ApprovedAnswer {
  return {
    id,
    questionText,
    answerText: 'Yes.',
    citations: [],
    approvedBy: 'U_SME',
    approvedAt: '2026-01-01',
    kind: 'evidence',
  };
}

describe('ConformalMatcher', () => {
  test('is uncalibrated before calibration', () => {
    const m = new ConformalMatcher();
    expect(m.isCalibrated).toBe(false);
    expect(m.match('anything', [answer(1, 'anything')])).toBeUndefined();
  });

  test('calibration produces a finite qHat', () => {
    const m = new ConformalMatcher(0.1);
    m.calibrate([
      { query: 'Do you encrypt data at rest?', candidate: 'Do you encrypt data at rest?', same: true },
      { query: 'Is MFA enforced?', candidate: 'Is MFA enforced?', same: true },
      { query: 'Do you encrypt data at rest?', candidate: 'Do you carry insurance?', same: false },
    ]);
    expect(m.isCalibrated).toBe(true);
    expect(m.qHat).toBeGreaterThanOrEqual(0);
  });

  test('returns singleton match when prediction set has exactly one candidate', () => {
    const m = new ConformalMatcher(0.1);
    m.calibrate([
      { query: 'Do you encrypt data at rest?', candidate: 'Do you encrypt data at rest?', same: true },
      { query: 'Do you encrypt customer data at rest?', candidate: 'Do you encrypt data at rest?', same: true },
      { query: 'Is MFA enforced?', candidate: 'Is MFA enforced?', same: true },
      { query: 'Is MFA enforced for all employees?', candidate: 'Is MFA enforced?', same: true },
    ]);

    const candidates = [answer(1, 'Do you encrypt data at rest?'), answer(2, 'Is MFA enforced?')];
    const match = m.match('Do you encrypt customer data at rest?', candidates);
    expect(match?.id).toBe(1);
  });

  test('returns undefined when prediction set is ambiguous', () => {
    const m = new ConformalMatcher(0.5); // permissive threshold
    m.calibrate([
      { query: 'Do you encrypt data at rest?', candidate: 'Do you encrypt data at rest?', same: true },
      { query: 'Is MFA enforced?', candidate: 'Is MFA enforced?', same: true },
    ]);

    // Both candidates are security questions; with a permissive threshold both may enter the set.
    const candidates = [answer(1, 'Do you encrypt data at rest?'), answer(2, 'Is MFA enforced?')];
    const match = m.match('security question', candidates);
    expect(match).toBeUndefined();
  });

  test('returns undefined when prediction set is empty', () => {
    const m = new ConformalMatcher(0.1);
    m.calibrate([
      { query: 'Do you encrypt data at rest?', candidate: 'Do you encrypt data at rest?', same: true },
    ]);

    const candidates = [answer(1, 'Do you encrypt data at rest?')];
    const match = m.match('lunch menu', candidates);
    expect(match).toBeUndefined();
  });

  test('nonconformity is symmetric and bounded', () => {
    const m = new ConformalMatcher();
    const a = m.score('Do you encrypt data at rest?', 'Do you encrypt data at rest?');
    const b = m.score('Do you encrypt data at rest?', 'Do you carry insurance?');
    expect(a).toBe(0);
    expect(b).toBeGreaterThan(a);
    expect(b).toBeLessThanOrEqual(1);
  });
});
