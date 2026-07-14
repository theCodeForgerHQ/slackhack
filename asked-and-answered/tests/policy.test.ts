import { describe, test, expect } from 'vitest';
import { selectPolicy, isFinalApproval, DEFAULT_POLICY, HIGH_SENSITIVITY_POLICY } from '../src/core/policy.js';

describe('selectPolicy', () => {
  test('defaults to two-gate for routine questions', () => {
    expect(selectPolicy('Do you encrypt data at rest?')).toEqual(DEFAULT_POLICY);
    expect(selectPolicy('Are backups tested quarterly?')).toEqual(DEFAULT_POLICY);
  });

  test('selects N-of-M for high-sensitivity questions', () => {
    expect(selectPolicy('Was the breach response classified?')).toEqual(HIGH_SENSITIVITY_POLICY);
    expect(selectPolicy('Who is the privacy officer?')).toEqual(HIGH_SENSITIVITY_POLICY);
    expect(selectPolicy('Is the SOC 2 Type II report confidential?')).toEqual(HIGH_SENSITIVITY_POLICY);
  });
});

describe('isFinalApproval', () => {
  test('one approver is final under default policy', () => {
    expect(isFinalApproval(['U1'], DEFAULT_POLICY)).toBe(true);
  });

  test('two distinct approvers are final under high-sensitivity policy', () => {
    expect(isFinalApproval(['U1', 'U2'], HIGH_SENSITIVITY_POLICY)).toBe(true);
  });

  test('duplicate approvers do not count twice', () => {
    expect(isFinalApproval(['U1', 'U1'], HIGH_SENSITIVITY_POLICY)).toBe(false);
  });
});
